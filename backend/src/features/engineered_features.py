import numpy as np
import pandas as pd

import config

REF = config.REFERENCE_PERIOD_FRACTION


def mad_scale(series):
    centre = series.median()
    spread = (series - centre).abs().median()
    value = 1.4826 * spread
    if not np.isfinite(value) or value < 1e-9:
        fallback = series.std()
        return float(fallback) if np.isfinite(fallback) and fallback > 1e-9 else 1.0
    return float(value)


def add_series_features(features):
    frame = features.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame = frame.sort_values(["station_id", "sensor_name", "timestamp"]).reset_index(drop=True)

    key = [frame["station_id"], frame["sensor_name"]]
    grouped = frame.groupby(["station_id", "sensor_name"], sort=False)

    value = frame["measured_value"].astype(float)
    frame["_value"] = value

    level_median = grouped["_value"].transform("median")
    level_scale = grouped["_value"].transform(mad_scale)
    level_scale = level_scale.where(level_scale > 1e-9, 1.0)

    trend = grouped["_value"].transform(
        lambda series: series.rolling(168, min_periods=24).median()
    ).fillna(level_median)
    detrended = value - trend

    seasonal = pd.DataFrame(
        {
            "station_id": frame["station_id"],
            "sensor_name": frame["sensor_name"],
            "hour": frame["timestamp"].dt.hour,
            "detrended": detrended,
        }
    ).groupby(["station_id", "sensor_name", "hour"])["detrended"].transform("median")
    residual = detrended - seasonal

    residual_scale = residual.groupby(key).transform(mad_scale).where(lambda s: s > 1e-9, 1.0)
    trend_scale = trend.groupby(key).transform(mad_scale).where(lambda s: s > 1e-9, 1.0)

    lagged = pd.concat(
        [grouped["_value"].shift(hours) for hours in (24, 48, 72, 96, 120, 144, 168)],
        axis=1,
    )
    forecast = lagged.median(axis=1)
    forecast_residual = value - forecast
    forecast_scale = forecast_residual.groupby(key).transform(mad_scale)
    forecast_scale = forecast_scale.where(forecast_scale > 1e-9, level_scale)

    frame["stl_residual_z"] = (residual / residual_scale).abs().clip(0.0, 60.0)
    frame["stl_trend_z"] = ((trend - level_median) / level_scale).abs().clip(0.0, 60.0)
    frame["stl_trend_slope_z"] = (
        (trend - grouped["_value"].shift(168).rolling(24, min_periods=8).median())
        / trend_scale
    ).abs().fillna(0.0).clip(0.0, 60.0)
    frame["forecast_residual_z"] = (forecast_residual / forecast_scale).abs().clip(0.0, 60.0)
    frame["forecast_bias"] = (forecast_residual / level_scale).clip(-30.0, 30.0)

    rate = grouped["_value"].diff()
    frame["rate_z"] = (rate.abs() / level_scale).fillna(0.0).clip(0.0, 60.0)
    frame["acceleration_z"] = (
        (rate.groupby(key).diff().abs() / level_scale).fillna(0.0)
    ).clip(0.0, 60.0)

    std_6 = grouped["_value"].transform(lambda series: series.rolling(6, min_periods=4).std())
    std_168 = grouped["_value"].transform(lambda series: series.rolling(168, min_periods=24).std())
    frame["flatline_ratio"] = (std_6 / level_scale).fillna(1.0).clip(0.0, 10.0)
    frame["volatility_ratio"] = (std_168 / level_scale).fillna(1.0).clip(0.0, 10.0)

    month = frame["timestamp"].dt.month.to_numpy()
    doy = frame["timestamp"].dt.dayofyear.to_numpy()
    frame["season_sin"] = np.sin(2.0 * np.pi * doy / 365.25)
    frame["season_cos"] = np.cos(2.0 * np.pi * doy / 365.25)

    for column in ("_value",):
        frame = frame.drop(columns=[column])
    return frame


def add_station_context(features):
    frame = features.copy()
    index = ["station_id", "timestamp"]

    residual_pivot = frame.pivot_table(
        index=index, columns="sensor_name", values="stl_residual_z", aggfunc="max", fill_value=0.0
    ).reindex(columns=list(config.SENSORS), fill_value=0.0)
    forecast_pivot = frame.pivot_table(
        index=index,
        columns="sensor_name",
        values="forecast_residual_z",
        aggfunc="max",
        fill_value=0.0,
    ).reindex(columns=list(config.SENSORS), fill_value=0.0)

    residual_max = residual_pivot.max(axis=1)
    residual_mean = residual_pivot.mean(axis=1)
    sensors_loud = (residual_pivot > 2.0).sum(axis=1).astype(float)
    forecast_max = forecast_pivot.max(axis=1)
    forecast_mean = forecast_pivot.mean(axis=1)

    regional = residual_mean.groupby(level="timestamp").transform("mean")

    for column, series in (
        ("station_residual_max", residual_max),
        ("station_residual_mean", residual_mean),
        ("station_sensors_loud", sensors_loud),
        ("station_forecast_max", forecast_max),
        ("station_forecast_mean", forecast_mean),
        ("station_regional_mean", regional),
    ):
        frame[column] = series.reindex(
            pd.MultiIndex.from_frame(frame[["station_id", "timestamp"]])
        ).to_numpy()

    frame["sensor_residual_share"] = (
        frame["stl_residual_z"].to_numpy()
        / np.maximum(frame["station_residual_max"].to_numpy(), 1e-6)
    )
    return frame


def build_engineered(features):
    return add_station_context(add_series_features(features))


SERIES_COLUMNS = [
    "stl_residual_z",
    "stl_trend_z",
    "stl_trend_slope_z",
    "forecast_residual_z",
    "forecast_bias",
    "rate_z",
    "acceleration_z",
    "flatline_ratio",
    "volatility_ratio",
    "season_sin",
    "season_cos",
]

CONTEXT_COLUMNS = [
    "station_residual_max",
    "station_residual_mean",
    "station_sensors_loud",
    "station_forecast_max",
    "station_forecast_mean",
    "station_regional_mean",
    "sensor_residual_share",
]


def feature_list():
    return list(config.FEATURE_COLUMNS) + SERIES_COLUMNS + CONTEXT_COLUMNS
