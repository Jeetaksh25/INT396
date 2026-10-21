from pathlib import Path

import config


def main():
    print("=" * 62)
    print(" INT396 · Sensor Fault Discovery")
    print("=" * 62)

    required = [
        config.DATASET_PARQUET,
        config.PROCESSED_DIR / "labels.parquet",
        config.METRICS_JSON,
        config.DETECTIONS_CSV,
        config.STATION_HEALTH_JSON,
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing: {path}")
        raise SystemExit("run the pipeline first")

    import json
    import pandas as pd
    from src.evaluation.metrics import evaluate_all

    detections = pd.read_csv(config.DETECTIONS_CSV, parse_dates=["timestamp"])
    labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
    labels["timestamp"] = pd.to_datetime(labels["timestamp"])

    metrics, merged = evaluate_all(
        detections,
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

    print("\nDetector")
    for key, value in metrics["detector"].items():
        print(f"  {key}: {value}")
    print("\nBaseline")
    for key, value in metrics["baseline_range_check"].items():
        print(f"  {key}: {value}")

    print("\nPer fault type")
    for fault_name, value in metrics["per_fault_type_recall"].items():
        baseline_value = metrics["baseline_per_fault_type_recall"][fault_name]
        print(f"  {fault_name:<10} detector {value:.3f}  baseline {baseline_value:.3f}")

    with open(config.METRICS_JSON, "r", encoding="utf-8") as handle:
        summary = json.load(handle)
    print("\nEvents")
    for key, value in summary["event_metrics"].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
