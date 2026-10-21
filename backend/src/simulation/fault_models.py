import numpy as np
import pandas as pd

import config


def sensor_sigma(clean_series):
    value = float(np.nanstd(clean_series.to_numpy(dtype=float)))
    if not np.isfinite(value) or value < 1e-6:
        return 1.0
    return value


def pick_window(length, window_hours, rng):
    if window_hours >= length:
        return 0, length
    start = int(rng.integers(0, length - window_hours))
    return start, start + window_hours


def inject_bias(clean_series, rng, sensor_name):
    sigma = sensor_sigma(clean_series)
    duration = int(rng.integers(12, 73))
    start, end = pick_window(len(clean_series), duration, rng)
    magnitude = float(rng.uniform(3.0, 8.0) * sigma)
    if rng.random() < 0.5:
        magnitude = -magnitude
    values = clean_series.to_numpy(dtype=float).copy()
    mask = np.zeros(len(values), dtype=bool)
    values[start:end] += magnitude
    mask[start:end] = True
    return values, mask


def inject_drift(clean_series, rng, sensor_name):
    sigma = sensor_sigma(clean_series)
    duration_days = int(rng.integers(3, 11))
    duration = duration_days * 24
    start, end = pick_window(len(clean_series), duration, rng)
    magnitude = float(rng.uniform(2.0, 5.0) * sigma)
    if rng.random() < 0.5:
        magnitude = -magnitude
    values = clean_series.to_numpy(dtype=float).copy()
    mask = np.zeros(len(values), dtype=bool)
    ramp = np.linspace(0.0, magnitude, end - start)
    values[start:end] += ramp
    mask[start:end] = True
    return values, mask


def inject_stuck(clean_series, rng, sensor_name):
    duration = int(rng.integers(6, 49))
    start, end = pick_window(len(clean_series), duration, rng)
    values = clean_series.to_numpy(dtype=float).copy()
    mask = np.zeros(len(values), dtype=bool)
    anchor = values[start + (end - start) // 2]
    if not np.isfinite(anchor):
        anchor = float(np.nanmean(values))
    values[start:end] = anchor
    mask[start:end] = True
    return values, mask


def inject_spike(clean_series, rng, sensor_name):
    sigma = sensor_sigma(clean_series)
    values = clean_series.to_numpy(dtype=float).copy()
    mask = np.zeros(len(values), dtype=bool)
    spike_rate = float(rng.uniform(0.01, 0.03))
    spike_count = max(1, int(len(values) * spike_rate))
    spike_indices = rng.choice(len(values), size=spike_count, replace=False)
    magnitudes = rng.uniform(5.0, 12.0, size=spike_count) * sigma
    signs = np.where(rng.random(spike_count) < 0.5, -1.0, 1.0)
    values[spike_indices] += magnitudes * signs
    mask[spike_indices] = True
    return values, mask


def inject_precision(clean_series, rng, sensor_name):
    duration = int(rng.integers(24, 121))
    start, end = pick_window(len(clean_series), duration, rng)
    quantum = float(rng.choice([1.0, 2.0, 5.0]))
    noise_scale = 2.0 * quantum
    values = clean_series.to_numpy(dtype=float).copy()
    mask = np.zeros(len(values), dtype=bool)
    window = values[start:end]
    rounded = quantum * np.round(window / quantum)
    noisy = rounded + rng.normal(0.0, noise_scale, size=len(window))
    values[start:end] = noisy
    mask[start:end] = True
    return values, mask


def inject_dropout(clean_series, rng, sensor_name):
    duration = int(rng.integers(3, 25))
    start, end = pick_window(len(clean_series), duration, rng)
    values = clean_series.to_numpy(dtype=float).copy()
    mask = np.zeros(len(values), dtype=bool)
    drop_fraction = float(rng.uniform(0.10, 0.40))
    window_length = end - start
    drop_count = max(1, int(window_length * drop_fraction))
    drop_indices = rng.choice(np.arange(start, end), size=drop_count, replace=False)
    values[drop_indices] = np.nan
    mask[start:end] = True
    return values, mask


FAULT_INJECTORS = {
    "bias": inject_bias,
    "drift": inject_drift,
    "stuck": inject_stuck,
    "spike": inject_spike,
    "precision": inject_precision,
    "dropout": inject_dropout,
}


def apply_fault_episodes(long_frame, rng):
    measured = long_frame["clean_value"].to_numpy(dtype=float).copy()
    fault_mask = np.zeros(len(long_frame), dtype=bool)
    fault_type = np.full(len(long_frame), "", dtype=object)
    episodes = []

    group_keys = list(long_frame.groupby(["station_id", "sensor_name"]).groups.keys())
    for fault_name in config.FAULT_TYPES:
        chosen_keys = rng.choice(len(group_keys), size=config.FAULT_EPISODES_PER_TYPE, replace=False)
        injector = FAULT_INJECTORS[fault_name]
        for key_index in chosen_keys:
            station_id, sensor_name = group_keys[int(key_index)]
            group_mask = (
                (long_frame["station_id"] == station_id)
                & (long_frame["sensor_name"] == sensor_name)
            )
            positions = np.flatnonzero(group_mask.to_numpy())
            clean_series = pd.Series(long_frame["clean_value"].to_numpy()[positions])
            faulted_values, local_mask = injector(clean_series, rng, sensor_name)
            global_positions = positions[local_mask]
            measured[global_positions] = faulted_values[local_mask]
            fault_mask[global_positions] = True
            fault_type[global_positions] = fault_name
            active = np.flatnonzero(local_mask)
            episodes.append(
                {
                    "fault_type": fault_name,
                    "station_id": station_id,
                    "sensor_name": sensor_name,
                    "start": str(long_frame["timestamp"].to_numpy()[global_positions].min()),
                    "end": str(long_frame["timestamp"].to_numpy()[global_positions].max()),
                    "affected_rows": int(len(global_positions)),
                    "start_index": int(active[0]),
                    "end_index": int(active[-1]),
                }
            )

    long_frame = long_frame.copy()
    long_frame["measured_value"] = measured
    long_frame["is_fault_injected"] = fault_mask.astype(int)
    long_frame["fault_type"] = fault_type
    return long_frame, episodes


def poisson_outage(wide_frame, rng, outage_hours=10):
    outage_start = int(rng.integers(0, len(wide_frame) - outage_hours))
    station_ids = wide_frame.index.get_level_values("station_id").unique()
    station_id = str(rng.choice(list(station_ids)))
    outage_frame = wide_frame.copy()
    positions = np.arange(outage_start, outage_start + outage_hours)
    station_positions = [
        position
        for position in positions
        if outage_frame.index[position][0] == station_id
    ]
    if station_positions:
        outage_frame.iloc[station_positions, :] = np.nan
    return outage_frame, station_id
