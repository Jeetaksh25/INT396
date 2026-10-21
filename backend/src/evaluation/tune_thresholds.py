import json
import sys

import numpy as np
import pandas as pd

import config
from src.detection.baseline_range_check import build_baseline_table
from src.detection.consensus_detector import compute_consensus
from src.detection.extreme_discriminator import apply_event_labels, classify_all_events
from src.evaluation.metrics import evaluate_all
from src.evaluation.run_experiment import build_wide_from_dataset, load_dataset
from src.features.feature_builder import (
    build_all_features,
    build_training_matrix,
    reference_mask_for,
)
from src.features.rule_features import mine_weather_rules, rule_violations_for_wide


def main():
    quantile = float(sys.argv[1]) if len(sys.argv) > 1 else config.REFERENCE_QUANTILE
    vote_threshold = int(sys.argv[2]) if len(sys.argv) > 2 else config.CONSENSUS_VOTE_THRESHOLD
    config.REFERENCE_QUANTILE = quantile
    config.CONSENSUS_VOTE_THRESHOLD = vote_threshold
    if len(sys.argv) > 3:
        config.NEIGHBOUR_DEVIATION_THRESHOLD = float(sys.argv[3])
    if len(sys.argv) > 4:
        config.NEIGHBOUR_AGREEMENT_THRESHOLD = float(sys.argv[4])

    dataset, clean_wide = load_dataset()
    rules = mine_weather_rules(clean_wide.reset_index())
    wide_measured = build_wide_from_dataset(dataset)
    measured_rules = rule_violations_for_wide(wide_measured, rules)

    features, _ = build_all_features(wide_measured, rule_violations=measured_rules)
    reference_mask = reference_mask_for(features)
    _, matrix, _ = build_training_matrix(features, reference_mask)

    detections, diagnostics = compute_consensus(features, matrix, reference_mask)
    baseline = build_baseline_table(features)
    detections = detections.merge(
        baseline[["station_id", "sensor_name", "timestamp", "baseline_flag"]],
        on=["station_id", "sensor_name", "timestamp"],
        how="left",
    )
    detections["timestamp"] = pd.to_datetime(detections["timestamp"])

    events = classify_all_events(detections, features)
    labelled = apply_event_labels(detections, events)

    labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
    labels["timestamp"] = pd.to_datetime(labels["timestamp"])
    metrics, merged = evaluate_all(
        labelled,
        labels[
            [
                "station_id",
                "timestamp",
                "sensor_name",
                "is_fault_injected",
                "fault_type",
                "is_extreme_event",
                "extreme_type",
            ]
        ],
    )

    summary = {
        "quantile": quantile,
        "vote_threshold": vote_threshold,
        "neighbour_deviation_threshold": config.NEIGHBOUR_DEVIATION_THRESHOLD,
        "neighbour_agreement_threshold": config.NEIGHBOUR_AGREEMENT_THRESHOLD,
        "fault_detection_rate": metrics["detector"]["fault_detection_rate"],
        "fault_classification_rate": metrics["detector"]["fault_classification_rate"],
        "extreme_false_flag_rate": metrics["detector"]["extreme_false_flag_rate"],
        "f1": metrics["detector"]["f1"],
        "precision": metrics["detector"]["precision"],
        "false_positive_rate_clean": metrics["detector"]["false_positive_rate_clean"],
        "precision_at_k": metrics["detector"]["precision_at_k"],
        "baseline_fdr": metrics["baseline_range_check"]["fault_detection_rate"],
        "baseline_effr": metrics["baseline_range_check"]["extreme_false_flag_rate"],
        "baseline_f1": metrics["baseline_range_check"]["f1"],
        "baseline_fpr": metrics["baseline_range_check"]["false_positive_rate_clean"],
        "per_fault_type_recall": metrics["per_fault_type_recall"],
        "event_count": int(len(events)),
        "anomaly_rows": int(labelled["is_anomaly"].sum()),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
