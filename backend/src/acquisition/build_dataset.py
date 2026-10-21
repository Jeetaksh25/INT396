import pandas as pd

import config


def load_station_frame(station_id):
    source_path = config.RAW_DIR / f"{station_id}.csv"
    frame = pd.read_csv(source_path, parse_dates=["timestamp"])
    frame = frame.set_index("timestamp").sort_index()
    start = pd.Timestamp(config.START_DATE)
    end = pd.Timestamp(config.END_DATE) + pd.Timedelta(hours=23)
    hourly_index = pd.date_range(start, end, freq="h")
    sensor_columns = list(config.SENSORS) + ["precipitation"]
    frame = frame.reindex(hourly_index)
    frame.index.name = "timestamp"
    for sensor_name in sensor_columns:
        frame[sensor_name] = pd.to_numeric(frame[sensor_name], errors="coerce")
        frame[sensor_name] = frame[sensor_name].interpolate(
            method="linear",
            limit=config.MAX_INTERPOLATION_GAP_HOURS,
            limit_direction="both",
        )
    frame = frame.dropna(subset=config.SENSORS, how="all")
    frame["station_id"] = station_id
    return frame[sensor_columns]


def build_clean_wide():
    station_frames = []
    for station_id in config.STATION_REGISTRY:
        station_frame = load_station_frame(station_id)
        station_frame["station_id"] = station_id
        station_frames.append(station_frame)
    wide_frame = pd.concat(station_frames)
    wide_frame = wide_frame.reset_index().set_index(["station_id", "timestamp"]).sort_index()
    return wide_frame


def build_clean_long(wide_frame):
    long_frame = wide_frame[list(config.SENSORS)].stack().reset_index()
    long_frame.columns = ["station_id", "timestamp", "sensor_name", "clean_value"]
    long_frame = long_frame.sort_values(["station_id", "sensor_name", "timestamp"]).reset_index(drop=True)
    long_frame["measured_value"] = long_frame["clean_value"]
    return long_frame


def save_clean_outputs(wide_frame, long_frame):
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    wide_frame.reset_index().to_parquet(config.PROCESSED_DIR / "clean_wide.parquet", index=False)
    long_frame.to_parquet(config.PROCESSED_DIR / "clean_long.parquet", index=False)
    sample = long_frame.groupby(["station_id", "sensor_name"], group_keys=False).head(20)
    sample.to_csv(config.SAMPLES_DIR / "dataset_sample.csv", index=False)
    return wide_frame, long_frame


def main():
    wide_frame = build_clean_wide()
    long_frame = build_clean_long(wide_frame)
    save_clean_outputs(wide_frame, long_frame)
    print(f"clean rows: {len(long_frame)} across {long_frame['station_id'].nunique()} stations")
    print(long_frame.groupby("sensor_name")["clean_value"].agg(["mean", "std", "min", "max"]))


if __name__ == "__main__":
    main()
