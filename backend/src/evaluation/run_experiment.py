import json
import time

import numpy as np
import pandas as pd

import config
from src.detection.baseline_range_check import build_baseline_table
from src.detection.consensus_detector import compute_consensus
from src.detection.extreme_discriminator import apply_event_labels, classify_all_events
from src.detection.station_health import build_station_health, save_station_health
from src.evaluation.metrics import build_event_metrics, evaluate_all
from src.features.feature_builder import (
    build_all_features,
    build_training_matrix,
    reference_mask_for,
)
from src.features.leakage_guard import assert_no_labels
from src.features.rule_features import mine_weather_rules, rule_violations_for_wide


def load_dataset():
    dataset = pd.read_parquet(config.DATASET_PARQUET)
    dataset["timestamp"] = pd.to_datetime(dataset["timestamp"])
    clean_wide = pd.read_parquet(config.PROCESSED_DIR / "clean_wide.parquet")
    clean_wide["timestamp"] = pd.to_datetime(clean_wide["timestamp"])
    clean_wide = clean_wide.set_index(["station_id", "timestamp"]).sort_index()
    return dataset, clean_wide


def build_wide_from_dataset(dataset):
    assert_no_labels(dataset, "detector input")
    wide = (
        dataset.pivot_table(
            index=["station_id", "timestamp"],
            columns="sensor_name",
            values="measured_value",
            aggfunc="first",
        )
        .reset_index()
        .set_index(["station_id", "timestamp"])
        .sort_index()
    )
    return wide[list(config.SENSORS)]


def run_pipeline(dataset, clean_wide):
    timing = {}
    start_time = time.time()

    rules = mine_weather_rules(clean_wide.reset_index())
    rule_violations = rule_violations_for_wide(clean_wide, rules)
    wide_measured = build_wide_from_dataset(dataset)
    measured_rule_violations = rule_violations_for_wide(wide_measured, rules)
    timing["rules_seconds"] = round(time.time() - start_time, 2)

    feature_start = time.time()
    features, station_stats = build_all_features(
        wide_measured, rule_violations=measured_rule_violations
    )
    assert_no_labels(features, "feature matrix")
    reference_mask = reference_mask_for(features)
    standardized_features, matrix, feature_stats = build_training_matrix(features, reference_mask)
    timing["features_seconds"] = round(time.time() - feature_start, 2)

    detector_start = time.time()
    detections, diagnostics = compute_consensus(features, matrix, reference_mask)
    timing["detector_seconds"] = round(time.time() - detector_start, 2)

    baseline = build_baseline_table(features)
    detections = detections.merge(
        baseline[["station_id", "sensor_name", "timestamp", "baseline_flag"]],
        on=["station_id", "sensor_name", "timestamp"],
        how="left",
    )
    detections["timestamp"] = pd.to_datetime(detections["timestamp"])

    discriminator_start = time.time()
    events_frame = classify_all_events(detections, standardized_features)
    assert_no_labels(detections, "detector output")
    labelled = apply_event_labels(detections, events_frame)
    timing["discriminator_seconds"] = round(time.time() - discriminator_start, 2)

    return {
        "features": features,
        "standardized_features": standardized_features,
        "detections": labelled,
        "events": events_frame,
        "diagnostics": diagnostics,
        "rules": len(rules),
        "reference_mask": reference_mask,
        "feature_stats": feature_stats,
        "station_stats": station_stats,
        "timing": timing,
    }


def build_timeline(detections):
    hourly = (
        detections.groupby("timestamp")
        .agg(
            anomaly_count=("is_anomaly", "sum"),
            fault_flagged=("is_fault_flagged", "sum"),
            extreme_flagged=("is_extreme_flagged", "sum"),
            reading_count=("is_anomaly", "size"),
        )
        .reset_index()
        .sort_values("timestamp")
    )
    hourly["anomaly_percent"] = (100.0 * hourly["anomaly_count"] / hourly["reading_count"]).round(3)
    network = (
        hourly.groupby("timestamp")
        .agg(
            anomaly_count=("anomaly_count", "sum"),
            fault_flagged=("fault_flagged", "sum"),
            extreme_flagged=("extreme_flagged", "sum"),
            reading_count=("reading_count", "sum"),
        )
        .reset_index()
    )
    network["anomaly_percent"] = (100.0 * network["anomaly_count"] / network["reading_count"]).round(3)
    network["timestamp"] = network["timestamp"].astype(str)
    return network.to_dict(orient="records")


def save_outputs(pipeline_result, labels):
    detections = pipeline_result["detections"]
    labels_for_merge = labels[
        ["station_id", "timestamp", "sensor_name", "is_fault_injected", "fault_type", "is_extreme_event", "extreme_type"]
    ].copy()

    metrics, merged = evaluate_all(detections, labels_for_merge)
    event_metrics = build_event_metrics(pipeline_result["events"], merged)

    health_rows = build_station_health(detections, pipeline_result["events"])
    save_station_health(health_rows)

    output_columns = [
        "station_id",
        "sensor_name",
        "timestamp",
        "measured_value",
        "anomaly_score",
        "vote_count",
        "is_anomaly",
        "event_label",
        "reason_code",
        "is_fault_flagged",
        "is_extreme_flagged",
        "baseline_flag",
        "kmeans_score",
        "dbscan_score",
        "pca_score",
        "isolation_score",
        "lof_score",
    ]
    detections_for_export = merged[output_columns].copy()
    detections_for_export["timestamp"] = detections_for_export["timestamp"].astype(str)
    detections_for_export.to_csv(config.DETECTIONS_CSV, index=False)

    events_for_export = pipeline_result["events"].copy()
    if len(events_for_export):
        events_for_export["start"] = events_for_export["start"].astype(str)
        events_for_export["end"] = events_for_export["end"].astype(str)
        events_for_export.to_csv(config.EVENTS_CSV, index=False)

    timeline = build_timeline(merged)
    with open(config.TIMELINE_JSON, "w", encoding="utf-8") as handle:
        json.dump(timeline, handle)

    summary = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "random_seed": config.RANDOM_SEED,
        "dataset": {
            "stations": list(config.STATION_REGISTRY),
            "sensors": list(config.SENSORS),
            "rows": int(len(merged)),
            "start": str(merged["timestamp"].min()),
            "end": str(merged["timestamp"].max()),
            "source": "Open-Meteo Historical Weather API (ERA5)",
        },
        "detector": metrics["detector"],
        "baseline_range_check": metrics["baseline_range_check"],
        "delta": metrics["delta"],
        "per_fault_type_recall": metrics["per_fault_type_recall"],
        "baseline_per_fault_type_recall": metrics["baseline_per_fault_type_recall"],
        "per_station": metrics["per_station"],
        "label_counts": metrics["label_counts"],
        "confusion": metrics["confusion"],
        "event_metrics": event_metrics,
        "diagnostics": pipeline_result["diagnostics"],
        "timing": pipeline_result["timing"],
        "rule_count": pipeline_result["rules"],
        "feature_columns": config.FEATURE_COLUMNS,
    }
    with open(config.METRICS_JSON, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, default=str)

    return summary, merged, health_rows


def main():
    dataset, clean_wide = load_dataset()
    pipeline_result = run_pipeline(dataset, clean_wide)
    labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
    labels["timestamp"] = pd.to_datetime(labels["timestamp"])
    summary, merged, health_rows = save_outputs(pipeline_result, labels)
    print(json.dumps({k: summary[k] for k in ["detector", "baseline_range_check", "delta"]}, indent=2))
    print(json.dumps(summary["per_fault_type_recall"], indent=2))
    print(json.dumps(summary["event_metrics"], indent=2))
    print(json.dumps(summary["diagnostics"], indent=2)[:800])


if __name__ == "__main__":
    main()
