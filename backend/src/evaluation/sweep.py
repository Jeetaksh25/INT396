import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.detection.baseline_range_check import build_baseline_table
from src.detection.consensus_detector import fit_consensus, score_with_bank
from src.detection.extreme_discriminator import apply_event_labels, classify_all_events
from src.evaluation.harness import metrics_for, prepare
from src.features.feature_builder import build_training_matrix, reference_mask_for

CACHE = Path(__file__).resolve().parent.parent.parent / "results" / "score_cache.npz"


def build_scores(force=False):
    if CACHE.exists() and not force:
        data = np.load(CACHE)
        return {key: data[key] for key in data.files}

    features, _ = prepare()
    reference_mask = reference_mask_for(features)
    _, matrix, _ = build_training_matrix(features, reference_mask)
    fitted = fit_consensus(matrix[reference_mask])
    scores, cluster_labels, components = score_with_bank(fitted["bank"], matrix)

    payload = {
        "kmeans_score": scores["kmeans_score"],
        "dbscan_score": scores["dbscan_score"],
        "pca_score": scores["pca_score"],
        "isolation_score": scores["isolation_score"],
        "lof_score": scores["lof_score"],
        "kmeans_cluster": cluster_labels["kmeans"],
        "dbscan_cluster": cluster_labels["dbscan"],
        "reference_mask": reference_mask,
        "pca_components": np.array([components]),
    }
    np.savez_compressed(CACHE, **payload)
    return payload


def assemble(features, scores, thresholds, vote_threshold, neighbour_dev, reference_mask):
    from src.features.feature_builder import rolling_mean, rolling_std

    values = features["measured_value"].astype(float)
    local_mean = rolling_mean(values)
    local_std = rolling_std(values).replace(0.0, np.nan).fillna(1.0)
    sensor_deviation = ((values - local_mean) / local_std).fillna(0.0)

    result = features[["station_id", "sensor_name", "timestamp", "measured_value"]].copy()
    result["sensor_deviation"] = sensor_deviation.to_numpy()

    votes = {}
    for name, name_scores in scores.items():
        votes[name.replace("_score", "_vote")] = (
            name_scores > thresholds[name.replace("_score", "_vote")]
        ).astype(int)

    vote_matrix = np.column_stack(list(votes.values()))
    vote_count = vote_matrix.sum(axis=1)
    is_anomaly = (vote_count >= vote_threshold).astype(int)

    anomaly_flags = pd.Series(is_anomaly, index=result.index)
    group_key = result["station_id"].astype(str) + "|" + result["sensor_name"].astype(str)
    local_flag = (
        (anomaly_flags == 1) & (result["sensor_deviation"].abs() > neighbour_dev)
    ).astype(int)
    per_group_anomalies = anomaly_flags.groupby(group_key).transform("sum")
    per_group_flagged = local_flag.groupby(group_key).transform("sum")
    fallback = (per_group_anomalies > 0) & (per_group_flagged == 0)
    is_local = (anomaly_flags == 1) & ((local_flag == 1) | fallback)

    result["is_local_anomaly"] = is_local.astype(int)
    for name, name_scores in scores.items():
        result[name] = name_scores
    for name, vote in votes.items():
        result[name] = vote
    result["vote_count"] = vote_count
    result["anomaly_score"] = vote_count / config.CONSENSUS_VOTE_TOTAL
    result["is_anomaly"] = is_anomaly
    result["kmeans_cluster"] = scores.get("kmeans_cluster", np.zeros(len(result), dtype=int))
    result["dbscan_cluster"] = scores.get("dbscan_cluster", np.zeros(len(result), dtype=int))
    return result


def thresholds_from_scores(scores, reference_mask, quantile):
    result = {}
    for name, name_scores in scores.items():
        reference_scores = name_scores[reference_mask]
        unique_values = np.unique(reference_scores)
        if len(unique_values) <= 2 and set(unique_values.tolist()).issubset({0.0, 1.0}):
            result[name.replace("_score", "_vote")] = 0.5
        else:
            result[name.replace("_score", "_vote")] = float(
                np.quantile(reference_scores, quantile)
            )
    return result


def run_config(quantile, vote_threshold, neighbour_dev, labels, features, scores, reference_mask):
    thresholds = thresholds_from_scores(scores, reference_mask, quantile)
    detections = assemble(
        features,
        scores,
        thresholds,
        vote_threshold,
        neighbour_dev,
        reference_mask,
    )

    baseline = build_baseline_table(features)
    detections = detections.merge(
        baseline[["station_id", "sensor_name", "timestamp", "baseline_flag"]],
        on=["station_id", "timestamp", "sensor_name"],
        how="left",
    )
    detections["timestamp"] = pd.to_datetime(detections["timestamp"])

    _, matrix, statistics = build_training_matrix(features, reference_mask)
    standardized = features.copy()
    for column in config.FEATURE_COLUMNS:
        values = standardized[column].astype(float)
        standardized[column] = (
            values - statistics[column]["mean"]
        ) / statistics[column]["std"]

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
    features, labels = prepare()
    scores = build_scores()
    reference_mask = scores["reference_mask"]
    score_map = {
        "kmeans_score": scores["kmeans_score"],
        "dbscan_score": scores["dbscan_score"],
        "pca_score": scores["pca_score"],
        "isolation_score": scores["isolation_score"],
        "lof_score": scores["lof_score"],
        "kmeans_cluster": scores["kmeans_cluster"],
        "dbscan_cluster": scores["dbscan_cluster"],
    }
    print("features", len(features), "scores ready", round(time.time() - started, 1))

    rows = []
    for quantile in (0.99, 0.98, 0.97, 0.95, 0.90):
        for vote_threshold in (3, 2, 1):
            for neighbour_dev in (2.5, 2.0, 1.5):
                result, _ = run_config(
                    quantile,
                    vote_threshold,
                    neighbour_dev,
                    labels,
                    features,
                    score_map,
                    reference_mask,
                )
                rows.append(
                    {
                        "q": quantile,
                        "vote": vote_threshold,
                        "ndev": neighbour_dev,
                        "acc": result["accuracy"],
                        "bal": result["balanced_accuracy"],
                        "macro_f1": result["macro_f1"],
                        "fault_r": result["per_class"]["fault"]["recall"],
                        "ext_r": result["per_class"]["extreme"]["recall"],
                        "clean_r": result["per_class"]["clean"]["recall"],
                        "bins": result["bins"],
                    }
                )
                print(
                    f"q={quantile} v={vote_threshold} nd={neighbour_dev} "
                    f"acc={result['accuracy']:.3f} bal={result['balanced_accuracy']:.3f} "
                    f"mF1={result['macro_f1']:.3f} f={result['per_class']['fault']['recall']:.3f} "
                    f"e={result['per_class']['extreme']['recall']:.3f}",
                    flush=True,
                )

    frame = pd.DataFrame(rows).sort_values("macro_f1", ascending=False)
    print("\nTOP BY MACRO F1")
    print(frame.head(10).to_string(index=False))
    frame.to_csv(Path(__file__).resolve().parent.parent.parent / "results" / "sweep.csv", index=False)
    print("elapsed", round(time.time() - started, 1))


if __name__ == "__main__":
    main()
