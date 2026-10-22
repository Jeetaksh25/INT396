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


def seasonal_climatology(station_frame, reference_hours, full_climatology=None):
    if full_climatology is not None:
        centre, spread = full_climatology
        keys = pd.MultiIndex.from_arrays(
            [station_frame.index.month, station_frame.index.hour]
        )
        centre_values = centre.reindex(keys).to_numpy()
        spread_values = spread.reindex(keys).to_numpy()
        spread_values = np.where(
            np.isfinite(spread_values) & (spread_values > 1e-9), spread_values, 1.0
        )
        deviation = np.abs(station_frame.to_numpy(dtype=float) - centre_values) / spread_values
        return pd.DataFrame(
            deviation, index=station_frame.index, columns=station_frame.columns
        )

    reference = station_frame.iloc[:reference_hours]
    keys = pd.DataFrame(
        {
            "month": station_frame.index.month,
            "hour": station_frame.index.hour,
        },
        index=station_frame.index,
    )

    month_hour_centre = reference.groupby(
        [reference.index.month, reference.index.hour]
    ).median()
    month_hour_spread = (
        reference.groupby([reference.index.month, reference.index.hour]).quantile(0.75)
        - reference.groupby([reference.index.month, reference.index.hour]).quantile(0.25)
    ).replace(0.0, np.nan)

    month_centre = reference.groupby(reference.index.month).median()
    month_spread = (
        reference.groupby(reference.index.month).quantile(0.75)
        - reference.groupby(reference.index.month).quantile(0.25)
    ).replace(0.0, np.nan)

    hour_centre = reference.groupby(reference.index.hour).median()
    hour_spread = (
        reference.groupby(reference.index.hour).quantile(0.75)
        - reference.groupby(reference.index.hour).quantile(0.25)
    ).replace(0.0, np.nan)

    overall_centre = reference.median()
    overall_spread = (reference.quantile(0.75) - reference.quantile(0.25)).replace(0.0, np.nan)
    observed_months = set(reference.index.month.unique())

    exact = pd.MultiIndex.from_arrays([keys["month"], keys["hour"]])
    centre_exact = month_hour_centre.reindex(exact).to_numpy()
    spread_exact = month_hour_spread.reindex(exact).to_numpy()

    same_month = keys["month"].isin(observed_months).to_numpy()
    month_centre_values = month_centre.reindex(keys["month"]).to_numpy()
    month_spread_values = month_spread.reindex(keys["month"]).to_numpy()
    hour_centre_values = hour_centre.reindex(keys["hour"]).to_numpy()
    hour_spread_values = hour_spread.reindex(keys["hour"]).to_numpy()

    overall_centre_values = np.repeat(
        overall_centre.to_numpy()[None, :], len(station_frame), axis=0
    )
    overall_spread_values = np.repeat(
        overall_spread.to_numpy()[None, :], len(station_frame), axis=0
    )

    centre = np.where(
        np.isnan(centre_exact),
        np.where(
            same_month[:, None],
            np.where(np.isnan(month_centre_values), hour_centre_values, month_centre_values),
            hour_centre_values,
        ),
        centre_exact,
    )
    spread = np.where(
        np.isnan(spread_exact),
        np.where(
            same_month[:, None],
            np.where(np.isnan(month_spread_values), hour_spread_values, month_spread_values),
            hour_spread_values,
        ),
        spread_exact,
    )

    centre = np.where(np.isnan(centre), overall_centre_values, centre)
    spread = np.where(np.isnan(spread), overall_spread_values, spread)
    spread = np.where(np.isnan(spread) | (spread <= 0.0), 1.0, spread)

    deviation = np.abs(station_frame.to_numpy(dtype=float) - centre) / spread
    return pd.DataFrame(deviation, index=station_frame.index, columns=station_frame.columns)


def build_full_climatology(station_frame):
    keys = pd.MultiIndex.from_arrays([station_frame.index.month, station_frame.index.hour])
    centre = station_frame.groupby(keys).median()
    spread = (
        station_frame.groupby(keys).quantile(0.75) - station_frame.groupby(keys).quantile(0.25)
    ).replace(0.0, np.nan)
    return centre, spread


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
        station_id: seasonal_climatology(
            station_frames[station_id],
            reference_hours,
            full_climatology=build_full_climatology(station_frames[station_id])
            if getattr(config, "USE_FULL_CLIMATOLOGY", False)
            else None,
        )
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
            long_mean = values.rolling(720, min_periods=168).mean()
            long_std = values.rolling(720, min_periods=168).std().replace(0.0, np.nan)
            long_baseline_z = ((values - long_mean) / long_std).abs()

            recent_mean = values.rolling(24, min_periods=12).mean()
            older_mean = values.shift(168).rolling(24, min_periods=12).mean()
            trend_168h = ((recent_mean - older_mean).abs() / long_std).fillna(0.0)

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
                    "long_baseline_z": long_baseline_z,
                    "trend_168h": trend_168h,
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


HEAVY_TAIL_COLUMNS = {
    "stl_residual_z",
    "stl_trend_z",
    "stl_trend_slope_z",
    "forecast_residual_z",
    "forecast_bias",
    "rate_z",
    "acceleration_z",
    "long_baseline_z",
    "trend_168h",
    "station_residual_max",
    "station_forecast_max",
}


def robust_scale(series, quantile=0.999):
    values = series.to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return 1.0
    scale = float(np.quantile(np.abs(finite), quantile))
    if not np.isfinite(scale) or scale < 1e-9:
        scale = float(np.std(finite))
    return scale if np.isfinite(scale) and scale > 1e-9 else 1.0


def build_training_matrix(features, reference_mask):
    standardized = features.copy()
    statistics = {}
    for column in config.FEATURE_COLUMNS:
        reference_values = standardized.loc[reference_mask, column].astype(float)
        mean_value = float(reference_values.median())
        if not np.isfinite(mean_value):
            mean_value = 0.0
        if column in HEAVY_TAIL_COLUMNS:
            std_value = robust_scale(reference_values)
            clipped = ((standardized[column].astype(float) - mean_value) / std_value).clip(-12.0, 12.0)
        else:
            std_value = float(reference_values.std())
            if not np.isfinite(std_value) or std_value < 1e-9:
                std_value = 1.0
            clipped = (standardized[column].astype(float) - mean_value) / std_value
        standardized[column] = clipped
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


def clean_reference_mask_for(features, fraction=None):
    timestamps = pd.to_datetime(features["timestamp"])
    if fraction is None:
        fraction = config.REFERENCE_PERIOD_FRACTION
    start = timestamps.min()
    end = timestamps.max()
    cutoff = start + (end - start) * fraction
    in_period = (timestamps <= cutoff).to_numpy()

    deviation = features["climatology_deviation"].astype(float).fillna(0.0).to_numpy()
    violation = (
        features["physics_violation_count"].astype(float).fillna(0.0).to_numpy()
        if "physics_violation_count" in features
        else np.zeros(len(features))
    )

    station_keys = features["station_id"].astype(str).to_numpy()
    frame = pd.DataFrame(
        {
            "station_id": station_keys,
            "timestamp": timestamps.to_numpy(),
            "deviation": deviation,
            "violation": violation,
        }
    )
    frame = frame.sort_values(["station_id", "timestamp"])
    smoothed = frame.groupby("station_id")["deviation"].transform(
        lambda series: series.rolling(24, min_periods=8).mean()
    )
    frame["sustained"] = smoothed.fillna(0.0)

    limit = float(frame["sustained"].quantile(config.CLEAN_REFERENCE_QUANTILE))
    flag = (
        (frame["sustained"] <= limit)
        & (frame["violation"] <= 0.0)
        & (frame["deviation"] <= float(frame["deviation"].quantile(0.98)))
    )
    frame["quiet"] = flag

    restored = frame.sort_index()
    mask = (restored["quiet"].to_numpy()) & in_period
    if mask.sum() < max(500, int(0.1 * len(features))):
        return in_period
    return mask
