import json

import numpy as np
import pandas as pd

import config


def build_labels(long_frame):
    labels = long_frame[["station_id", "timestamp", "sensor_name"]].copy()
    labels["is_fault_injected"] = long_frame["is_fault_injected"].astype(int)
    labels["fault_type"] = long_frame["fault_type"].fillna("")
    labels["is_extreme_event"] = long_frame["is_extreme_event"].astype(int)
    labels["extreme_type"] = long_frame["extreme_type"].fillna("")

    labels["is_anomaly"] = (
        (labels["is_fault_injected"] == 1) | (labels["is_extreme_event"] == 1)
    ).astype(int)

    labels["label_class"] = "clean"
    labels.loc[labels["is_extreme_event"] == 1, "label_class"] = "EXTREME"
    labels.loc[labels["is_fault_injected"] == 1, "label_class"] = "FAULT"
    return labels


def summarise_labels(labels):
    total_labels = len(labels)
    fault_rows = int(labels["is_fault_injected"].sum())
    extreme_rows = int(labels["is_extreme_event"].sum())
    summary = {
        "total_readings": int(total_labels),
        "fault_readings": fault_rows,
        "extreme_readings": extreme_rows,
        "fault_percent": round(100.0 * fault_rows / total_labels, 3),
        "extreme_percent": round(100.0 * extreme_rows / total_labels, 3),
        "fault_type_counts": {
            fault_name: int((labels["fault_type"] == fault_name).sum())
            for fault_name in config.FAULT_TYPES
        },
        "extreme_type_counts": {
            extreme_name: int((labels["extreme_type"] == extreme_name).sum())
            for extreme_name in config.EXTREME_TYPES
        },
        "per_station": {
            station_id: {
                "fault_readings": int(group["is_fault_injected"].sum()),
                "extreme_readings": int(group["is_extreme_event"].sum()),
            }
            for station_id, group in labels.groupby("station_id")
        },
    }
    return summary


def save_label_artifacts(labels, episodes, extreme_episodes):
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    labels.to_parquet(config.PROCESSED_DIR / "labels.parquet", index=False)
    summary = summarise_labels(labels)
    summary["fault_episodes"] = episodes
    summary["extreme_episodes"] = extreme_episodes
    with open(config.PROCESSED_DIR / "label_summary.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, default=str)
    return summary


def main():
    dataset = pd.read_csv(
        config.DATASET_CSV,
        parse_dates=["timestamp"],
        keep_default_na=False,
        na_values=[""],
    )
    labels = build_labels(dataset)
    labels.to_parquet(config.PROCESSED_DIR / "labels.parquet", index=False)
    print(json.dumps(summarise_labels(labels), indent=2))


if __name__ == "__main__":
    main()
