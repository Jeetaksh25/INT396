import numpy as np

import config


def range_check_flags(measured_values, sensor_names):
    flags = np.zeros(len(measured_values), dtype=int)
    for position, sensor_name in enumerate(sensor_names):
        value = measured_values[position]
        lower, upper = config.PHYSICAL_LIMITS[sensor_name]
        if not np.isfinite(value):
            flags[position] = 1
        elif value < lower or value > upper:
            flags[position] = 1
    return flags


def build_baseline_table(features):
    sensor_names = features["sensor_name"].to_numpy()
    measured_values = features["measured_value"].to_numpy(dtype=float)
    flags = np.zeros(len(features), dtype=int)
    for sensor_name in config.SENSORS:
        positions = np.flatnonzero(sensor_names == sensor_name)
        if len(positions) == 0:
            continue
        lower, upper = config.PHYSICAL_LIMITS[sensor_name]
        values = measured_values[positions]
        invalid = (~np.isfinite(values)) | (values < lower) | (values > upper)
        flags[positions] = invalid.astype(int)
    baseline = features[["station_id", "sensor_name", "timestamp", "measured_value"]].copy()
    baseline["baseline_flag"] = flags
    return baseline
