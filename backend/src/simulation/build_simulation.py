import json

import numpy as np
import pandas as pd

import config
from src.simulation.fault_models import apply_fault_episodes
from src.simulation.extreme_events import apply_extreme_episodes
from src.simulation.label_builder import save_label_artifacts


def build_faulted_dataset():
    clean_wide_path = config.PROCESSED_DIR / "clean_wide.parquet"
    if not clean_wide_path.exists():
        raise FileNotFoundError(
            "clean_wide.parquet missing. run `python -m src.acquisition.build_dataset` first."
        )
    wide_frame = pd.read_parquet(clean_wide_path)
    wide_frame = wide_frame.set_index(["station_id", "timestamp"]).sort_index()

    rng = np.random.default_rng(config.RANDOM_SEED)

    wide_frame, extreme_episodes = apply_extreme_episodes(wide_frame, rng)

    long_frame = wide_frame[list(config.SENSORS)].stack().reset_index()
    long_frame.columns = ["station_id", "timestamp", "sensor_name", "clean_value"]
    long_frame = long_frame.sort_values(
        ["station_id", "sensor_name", "timestamp"]
    ).reset_index(drop=True)

    long_frame["is_extreme_event"] = (
        wide_frame["is_extreme_event"]
        .reindex(pd.MultiIndex.from_frame(long_frame[["station_id", "timestamp"]]))
        .to_numpy()
    )
    long_frame["extreme_type"] = (
        wide_frame["extreme_type"]
        .reindex(pd.MultiIndex.from_frame(long_frame[["station_id", "timestamp"]]))
        .to_numpy()
    )

    fault_rng = np.random.default_rng(config.RANDOM_SEED + 1)
    long_frame, fault_episodes = apply_fault_episodes(long_frame, fault_rng)

    long_frame = long_frame[
        [
            "station_id",
            "timestamp",
            "sensor_name",
            "measured_value",
            "clean_value",
            "fault_type",
            "is_fault_injected",
            "is_extreme_event",
            "extreme_type",
        ]
    ]

    fault_summary = save_label_artifacts(
        long_frame.assign(
            fault_type=long_frame["fault_type"].fillna(""),
            extreme_type=long_frame["extreme_type"].fillna(""),
        ),
        fault_episodes,
        extreme_episodes,
    )

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    long_frame.to_csv(config.DATASET_CSV, index=False)
    long_frame.to_parquet(config.DATASET_PARQUET, index=False)
    return long_frame, fault_summary


def main():
    dataset, summary = build_faulted_dataset()
    print(f"rows: {len(dataset)}")
    print(json.dumps(summary, indent=2)[:1500])
    print(dataset.groupby("sensor_name")["measured_value"].describe())


if __name__ == "__main__":
    main()
