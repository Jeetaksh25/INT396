import numpy as np
import pandas as pd

import config


def rolling_median(series, window=24):
    return series.rolling(window=window, min_periods=max(3, window // 4)).median()


def rolling_mean(series, window=24):
    return series.rolling(window=window, min_periods=max(3, window // 4)).mean()


def rolling_std(series, window=24):
    return series.rolling(window=window, min_periods=max(3, window // 4)).std()


def flatline_score(series, window=6):
    rounded = series.round(2)
    identical = rounded.diff().abs().fillna(1.0) < 1e-9
    streaks = identical.astype(int).rolling(window=window, min_periods=window).sum()
    return (streaks >= window - 1).astype(float)


def compute_station_reference_stats(station_frame, reference_hours):
    stats = {}
    for sensor_name in config.SENSORS:
        values = station_frame[sensor_name].astype(float).iloc[:reference_hours]
        mean_value = float(values.mean())
        std_value = float(values.std())
        if not np.isfinite(std_value) or std_value < 1e-9:
            std_value = 1.0
        stats[sensor_name] = {"mean": mean_value, "std": std_value}
    return stats


def standardize_sensor(series, sensor_stats):
    return (series.astype(float) - sensor_stats["mean"]) / sensor_stats["std"]


def build_neighbour_deviation(station_id, sensor_name, station_frames, station_stats, timestamp_index):
    deviation_columns = []
    for other_id, other_frame in station_frames.items():
        if other_id == station_id:
            continue
        other_values = standardize_sensor(other_frame[sensor_name], station_stats[other_id][sensor_name])
        deviation_columns.append(other_values.abs())
    if not deviation_columns:
        return pd.Series(0.0, index=timestamp_index)
    neighbour_matrix = pd.concat(deviation_columns, axis=1)
    return neighbour_matrix.mean(axis=1)


def physical_rule_violations(station_frame):
    temperature = station_frame["temperature"].astype(float)
    humidity = station_frame["humidity"].astype(float)
    wind_speed = station_frame["wind_speed"].astype(float)
    pressure = station_frame["pressure"].astype(float)
    dew_point = temperature - (100.0 - humidity) / 5.0
    violation_count = (
        (dew_point > temperature + 1.0).astype(int)
        + ((humidity < 0.0) | (humidity > 100.0)).astype(int)
        + (wind_speed < 0.0).astype(int)
        + ((temperature < -60.0) | (temperature > 60.0)).astype(int)
        + ((pressure < 870.0) | (pressure > 1085.0)).astype(int)
    )
    return violation_count


def seasonal_climatology(station_frame, reference_hours):
    reference = station_frame.iloc[:reference_hours]
    reference_keys = pd.DataFrame(
        {"month": reference.index.month, "hour": reference.index.hour}, index=reference.index
    )
    centre = reference.groupby([reference_keys["month"], reference_keys["hour"]]).median()
    spread = (
        reference.groupby([reference_keys["month"], reference_keys["hour"]]).quantile(0.75)
        - reference.groupby([reference_keys["month"], reference_keys["hour"]]).quantile(0.25)
    ).replace(0.0, np.nan)
    keys = pd.DataFrame(
        {"month": station_frame.index.month, "hour": station_frame.index.hour},
        index=station_frame.index,
    )
    target = pd.MultiIndex.from_arrays([keys["month"], keys["hour"]])
    centre = centre.reindex(target).to_numpy()
    spread = spread.reindex(target).to_numpy()
    deviation = np.abs(station_frame.to_numpy(dtype=float) - centre) / spread
    deviation = pd.DataFrame(deviation, index=station_frame.index, columns=station_frame.columns)
    return deviation.fillna(0.0)


def build_context_columns(station_id, station_frame, station_frames, deviation_frames, timestamp_index):
    own_deviation = deviation_frames[station_id]
    other_names = [name for name in config.SENSORS]

    others_mean = pd.DataFrame(index=timestamp_index)
    for sensor_name in config.SENSORS:
        other_sensors = [name for name in other_names if name != sensor_name]
        others_mean[sensor_name] = own_deviation[other_sensors].mean(axis=1)

    neighbour_share = pd.DataFrame(index=timestamp_index)
    for sensor_name in config.SENSORS:
        columns = []
        for other_id, other_frame in deviation_frames.items():
            if other_id == station_id:
                continue
            columns.append(
                (other_frame[sensor_name] > config.COHERENT_DEVIATION_THRESHOLD).astype(float)
            )
        neighbour_share[sensor_name] = (
            pd.concat(columns, axis=1).mean(axis=1).reindex(timestamp_index).fillna(0.0)
            if columns
            else 0.0
        )

    return own_deviation, others_mean, neighbour_share


def build_all_features(wide_frame, rule_violations=None, rule_scores=None):
    station_frames = {
        station_id: group.droplevel("station_id")
        for station_id, group in wide_frame.groupby(level="station_id")
    }
    station_ids = list(station_frames)
    hours_per_station = len(station_frames[station_ids[0]])
    reference_hours = int(hours_per_station * config.REFERENCE_PERIOD_FRACTION)

    station_stats = {
        station_id: compute_station_reference_stats(station_frames[station_id], reference_hours)
        for station_id in station_ids
    }

    standardized_by_station = {
        station_id: pd.DataFrame(
            {
                sensor_name: standardize_sensor(
                    station_frames[station_id][sensor_name],
                    station_stats[station_id][sensor_name],
                )
                for sensor_name in config.SENSORS
            }
        )
        for station_id in station_ids
    }
    deviation_frames = {
        station_id: seasonal_climatology(station_frames[station_id], reference_hours)
        for station_id in station_ids
    }
    feature_blocks = []
    for station_id in station_ids:
        station_frame = station_frames[station_id]
        timestamp_index = station_frame.index
        standardized_by_sensor = standardized_by_station[station_id]

        hour_values = timestamp_index.hour.to_numpy()
        hour_angle = 2.0 * np.pi * hour_values / 24.0
        hour_sin = pd.Series(np.sin(hour_angle), index=timestamp_index)
        hour_cos = pd.Series(np.cos(hour_angle), index=timestamp_index)

        own_deviation, others_mean, neighbour_share = build_context_columns(
            station_id,
            station_frame,
            station_frames,
            deviation_frames,
            timestamp_index,
        )
        coherent_deviation_frame = (own_deviation > config.COHERENT_DEVIATION_THRESHOLD).astype(float)
        cross_sensor_count = (others_mean > config.COHERENT_DEVIATION_THRESHOLD).sum(axis=1)

        violations = physical_rule_violations(station_frame)
        if rule_violations is None:
            association_violations = violations.to_numpy(dtype=float)
        else:
            association_violations = rule_violations.loc[station_id].reindex(timestamp_index).fillna(0.0).to_numpy()

        for sensor_name in config.SENSORS:
            values = station_frame[sensor_name].astype(float)
            block = pd.DataFrame(
                {
                    "value_standardized": standardized_by_sensor[sensor_name],
                    "deviation_from_median_24h": values - rolling_median(values),
                    "rate_of_change": values.diff(),
                    "rolling_mean_24h": rolling_mean(values),
                    "rolling_std_24h": rolling_std(values),
                    "flatline_score": flatline_score(values),
                    "climatology_deviation": own_deviation[sensor_name].to_numpy(),
                    "other_sensor_deviation": others_mean[sensor_name].to_numpy(),
                    "coherent_deviation": coherent_deviation_frame[sensor_name].to_numpy(),
                    "cross_sensor_count": cross_sensor_count.to_numpy(),
                    "neighbour_share": neighbour_share[sensor_name].to_numpy(),
                    "hour_of_day_sin": hour_sin,
                    "hour_of_day_cos": hour_cos,
                    "rule_violation_count": association_violations.astype(float),
                    "physics_violation_count": violations.astype(float),
                    "missing_reading": values.isna().astype(float),
                }
            )
            block["station_id"] = station_id
            block["sensor_name"] = sensor_name
            block["timestamp"] = timestamp_index
            block["measured_value"] = values.to_numpy()
            feature_blocks.append(block)

    features = pd.concat(feature_blocks, ignore_index=True)
    features = features.sort_values(["station_id", "sensor_name", "timestamp"]).reset_index(drop=True)
    return features, station_stats


def build_training_matrix(features, reference_mask):
    standardized = features.copy()
    statistics = {}
    for column in config.FEATURE_COLUMNS:
        reference_values = standardized.loc[reference_mask, column].astype(float)
        mean_value = float(reference_values.mean())
        std_value = float(reference_values.std())
        if not np.isfinite(std_value) or std_value < 1e-9:
            std_value = 1.0
        if not np.isfinite(mean_value):
            mean_value = 0.0
        standardized[column] = (standardized[column].astype(float) - mean_value) / std_value
        statistics[column] = {"mean": mean_value, "std": std_value}
    standardized[config.FEATURE_COLUMNS] = standardized[config.FEATURE_COLUMNS].fillna(0.0)
    standardized[config.FEATURE_COLUMNS] = standardized[config.FEATURE_COLUMNS].replace(
        [np.inf, -np.inf], 0.0
    )
    matrix = standardized[config.FEATURE_COLUMNS].to_numpy(dtype=float)
    return standardized, matrix, statistics


def reference_mask_for(features, fraction=config.REFERENCE_PERIOD_FRACTION):
    timestamps = pd.to_datetime(features["timestamp"])
    start = timestamps.min()
    end = timestamps.max()
    cutoff = start + (end - start) * fraction
    return (timestamps <= cutoff).to_numpy()
