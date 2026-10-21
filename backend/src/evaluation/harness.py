import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.detection.baseline_range_check import build_baseline_table
from src.detection.consensus_detector import (
    assemble_detections,
    fit_consensus,
    score_with_bank,
    score_with_bank,
)
from src.detection.extreme_discriminator import apply_event_labels, classify_all_events
from src.evaluation.run_experiment import build_wide_from_dataset
from src.features.feature_builder import (
    build_all_features,
    build_training_matrix,
    reference_mask_for,
)
from src.features.leakage_guard import assert_no_labels
from src.features.rule_features import mine_weather_rules, rule_violations_for_wide
from src.simulation.build_simulation import build_faulted_dataset

CACHE = Path(__file__).resolve().parent.parent.parent / "results" / "harness_cache.npz"
FEATURES_CACHE = Path(__file__).resolve().parent.parent.parent / "results" / "harness_features.parquet"


def prepare(force=False):
    if FEATURES_CACHE.exists() and not force:
        features = pd.read_parquet(FEATURES_CACHE)
        labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
        labels["timestamp"] = pd.to_datetime(labels["timestamp"])
        return features, labels

    dataset = pd.read_parquet(config.DATASET_PARQUET)
    clean_wide = pd.read_parquet(config.PROCESSED_DIR / "clean_wide.parquet")
    clean_wide["timestamp"] = pd.to_datetime(clean_wide["timestamp"])
    clean_wide = clean_wide.set_index(["station_id", "timestamp"]).sort_index()
    dataset = dataset[
        ["station_id", "timestamp", "sensor_name", "measured_value"]
    ].copy()
    assert_no_labels(dataset, "harness input")

    rules = mine_weather_rules(clean_wide.reset_index())
    wide_measured = build_wide_from_dataset(dataset)
    measured_rules = rule_violations_for_wide(wide_measured, rules)
    features, _ = build_all_features(wide_measured, rule_violations=measured_rules)
    features.to_parquet(FEATURES_CACHE, index=False)

    labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
    labels["timestamp"] = pd.to_datetime(labels["timestamp"])
    return features, labels


def truth_vector(merged):
    fault = merged["is_fault_injected"].to_numpy() == 1
    extreme = merged["is_extreme_event"].to_numpy() == 1
    truth = np.where(fault, "fault", np.where(extreme, "extreme", "clean"))
    return truth


def decision_vector(merged):
    label = merged["event_label"].fillna("").to_numpy()
    decision = np.full(len(merged), "HEALTHY", dtype=object)
    decision[label == "FAULT"] = "FAULT"
    decision[label == "EXTREME"] = "EXTREME"
    return decision


def metrics_for(merged):
    truth = truth_vector(merged)
    decision = decision_vector(merged)
    expected = np.where(
        truth == "fault", "FAULT", np.where(truth == "extreme", "EXTREME", "HEALTHY")
    )
    correct = decision == expected
    accuracy = float(correct.mean())

    per_class = {}
    for name, truth_key, decision_key in (
        ("fault", "fault", "FAULT"),
        ("extreme", "extreme", "EXTREME"),
        ("clean", "clean", "HEALTHY"),
    ):
        mask = truth == truth_key
        total = int(mask.sum())
        hit = int((correct & mask).sum())
        per_class[name] = {
            "total": total,
            "recall": round(hit / total, 4) if total else 0.0,
        }

    recalls = [block["recall"] for block in per_class.values() if block["total"]]
    balanced = float(np.mean(recalls)) if recalls else 0.0

    f1_scores = []
    for name, truth_key, decision_key in (
        ("fault", "fault", "FAULT"),
        ("extreme", "extreme", "EXTREME"),
        ("clean", "clean", "HEALTHY"),
    ):
        true_positive = int(((decision == decision_key) & (truth == truth_key)).sum())
        predicted = int((decision == decision_key).sum())
        actual = int((truth == truth_key).sum())
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        f1_scores.append(
            {
                "class": name,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "predicted": predicted,
                "actual": actual,
            }
        )

    macro_f1 = float(np.mean([block["f1"] for block in f1_scores]))

    bins = {
        "healthy": int((decision == "HEALTHY").sum()),
        "fault": int((decision == "FAULT").sum()),
        "extreme": int((decision == "EXTREME").sum()),
    }

    return {
        "accuracy": round(accuracy, 4),
        "balanced_accuracy": round(balanced, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "class_reports": f1_scores,
        "bins": bins,
        "share": {
            "clean": round(float((truth == "clean").mean()), 4),
            "fault": round(float((truth == "fault").mean()), 4),
            "extreme": round(float((truth == "extreme").mean()), 4),
        },
    }


def evaluate_pipeline(quantile=None, vote_threshold=None, neighbour_dev=None, feature_columns=None):
    if quantile is not None:
        config.REFERENCE_QUANTILE = quantile
    if vote_threshold is not None:
        config.CONSENSUS_VOTE_THRESHOLD = vote_threshold
    if neighbour_dev is not None:
        config.NEIGHBOUR_DEVIATION_THRESHOLD = neighbour_dev

    features, labels = prepare()
    if feature_columns is not None:
        config.FEATURE_COLUMNS = feature_columns

    reference_mask = reference_mask_for(features)
    standardized, matrix, statistics = build_training_matrix(features, reference_mask)

    fitted = fit_consensus(matrix[reference_mask])
    scores, cluster_labels, components = score_with_bank(fitted["bank"], matrix)
    detections = assemble_detections(features, scores, cluster_labels, fitted["thresholds"])
    detections["pca_components"] = components

    baseline = build_baseline_table(features)
    detections = detections.merge(
        baseline[["station_id", "sensor_name", "timestamp", "baseline_flag"]],
        on=["station_id", "timestamp", "sensor_name"],
        how="left",
    )
    detections["timestamp"] = pd.to_datetime(detections["timestamp"])

    events = classify_all_events(detections, standardized)
    labelled = apply_event_labels(detections, events)

    merged = labelled.merge(
        labels[
            [
                "station_id",
                "timestamp",
                "sensor_name",
                "is_fault_injected",
                "is_extreme_event",
                "fault_type",
            ]
        ],
        on=["station_id", "timestamp", "sensor_name"],
        how="left",
    )
    merged["is_fault_injected"] = merged["is_fault_injected"].fillna(0).astype(int)
    merged["is_extreme_event"] = merged["is_extreme_event"].fillna(0).astype(int)

    return metrics_for(merged), merged


def main():
    started = time.time()
    result, merged = evaluate_pipeline()
    print(json.dumps(result, indent=2))
    print("elapsed", round(time.time() - started, 1))


if __name__ == "__main__":
    main()
