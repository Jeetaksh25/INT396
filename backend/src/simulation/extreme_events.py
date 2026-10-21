import numpy as np
import pandas as pd

import config

SEASON_MONTHS = {
    "heat_wave": [4, 5, 6, 7],
    "cold_snap": [12, 1, 2],
    "storm": [6, 7, 8, 9],
    "heavy_rain": [6, 7, 8, 9],
}


def raised_cosine(length, magnitude):
    if length <= 1:
        return np.array([magnitude], dtype=float)
    positions = np.linspace(0.0, 1.0, length)
    shape = 0.5 * (1.0 - np.cos(2.0 * np.pi * positions))
    return magnitude * shape


def candidate_starts(timestamps, months, duration, rng, attempts=400, fallback_all=False):
    months_array = timestamps.dt.month.to_numpy()
    valid = np.flatnonzero(np.isin(months_array, months))
    valid = valid[valid < len(timestamps) - duration]
    if len(valid) == 0 and fallback_all:
        valid = np.flatnonzero(months_array == months_array[0])
        valid = valid[valid < len(timestamps) - duration]
    if len(valid) == 0:
        return None
    return int(rng.choice(valid))


def neighbour_station(station_id, rng):
    other_ids = [other for other in config.STATION_REGISTRY if other != station_id]
    return str(rng.choice(other_ids))


def apply_heat_wave(station_frame, start, duration, rng):
    profile = raised_cosine(duration, float(rng.uniform(6.0, 12.0)))
    humidity_drop = raised_cosine(duration, float(rng.uniform(10.0, 25.0)))
    pressure_drop = raised_cosine(duration, float(rng.uniform(1.0, 4.0)))
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("temperature")] += profile
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("humidity")] -= humidity_drop
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("pressure")] -= pressure_drop
    return station_frame


def apply_cold_snap(station_frame, start, duration, rng):
    profile = raised_cosine(duration, float(rng.uniform(6.0, 15.0)))
    wind_gain = raised_cosine(duration, float(rng.uniform(2.0, 8.0)))
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("temperature")] -= profile
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("wind_speed")] += wind_gain
    return station_frame


def apply_storm(station_frame, start, duration, rng):
    wind_factor = raised_cosine(duration, float(rng.uniform(1.0, 2.5)))
    pressure_drop = raised_cosine(duration, float(rng.uniform(8.0, 20.0)))
    humidity_gain = raised_cosine(duration, float(rng.uniform(10.0, 20.0)))
    wind_positions = station_frame.columns.get_loc("wind_speed")
    station_frame.iloc[start:start + duration, wind_positions] *= (1.0 + wind_factor)
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("pressure")] -= pressure_drop
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("humidity")] += humidity_gain
    return station_frame


def apply_heavy_rain(station_frame, start, duration, rng):
    humidity_gain = raised_cosine(duration, float(rng.uniform(15.0, 35.0)))
    temperature_drop = raised_cosine(duration, float(rng.uniform(2.0, 6.0)))
    wind_gain = raised_cosine(duration, float(rng.uniform(3.0, 10.0)))
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("humidity")] += humidity_gain
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("temperature")] -= temperature_drop
    station_frame.iloc[start:start + duration, station_frame.columns.get_loc("wind_speed")] += wind_gain
    return station_frame


EXTREME_APPLIERS = {
    "heat_wave": apply_heat_wave,
    "cold_snap": apply_cold_snap,
    "storm": apply_storm,
    "heavy_rain": apply_heavy_rain,
}

EXTREME_DURATIONS = {
    "heat_wave": (72, 168),
    "cold_snap": (48, 120),
    "storm": (12, 36),
    "heavy_rain": (6, 24),
}


def clip_to_physical_bounds(station_frame):
    for sensor_name, (lower, upper) in config.PHYSICAL_LIMITS.items():
        station_frame[sensor_name] = station_frame[sensor_name].clip(lower, upper)
    return station_frame


def apply_extreme_episodes(wide_frame, rng, episodes_per_type=None):
    working_frame = wide_frame.reset_index()
    working_frame = working_frame.sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    is_extreme = np.zeros(len(working_frame), dtype=int)
    extreme_type = np.full(len(working_frame), "", dtype=object)
    episodes = []
    station_ids = list(config.STATION_REGISTRY)

    for extreme_name in config.EXTREME_TYPES:
        applier = EXTREME_APPLIERS[extreme_name]
        duration_low, duration_high = EXTREME_DURATIONS[extreme_name]
        per_type = (
            config.EXTREME_EPISODES_PER_TYPE if episodes_per_type is None else episodes_per_type
        )
        if per_type <= 0:
            continue
        chosen_stations = rng.choice(
            len(station_ids),
            size=min(per_type, len(station_ids) * 2),
            replace=True,
        )
        used = set()
        for station_index in chosen_stations:
            station_id = station_ids[int(station_index)]
            station_mask = working_frame["station_id"] == station_id
            station_positions = np.flatnonzero(station_mask.to_numpy())
            if len(station_positions) == 0:
                continue
            station_slice = working_frame.iloc[station_positions].copy()
            timestamps = station_slice["timestamp"].reset_index(drop=True)
            duration = int(rng.integers(duration_low, duration_high + 1))
            start = candidate_starts(
                timestamps,
                SEASON_MONTHS[extreme_name],
                duration,
                rng,
                fallback_all=True,
            )
            if start is None or (station_id, start) in used:
                continue
            used.add((station_id, start))
            local = station_slice[list(config.SENSORS)].reset_index(drop=True)
            local = clip_to_physical_bounds(local)
            local = applier(local, start, duration, rng)
            local = clip_to_physical_bounds(local)
            global_positions = station_positions[start:start + duration]
            working_frame.loc[global_positions, list(config.SENSORS)] = local.iloc[start:start + duration].to_numpy()
            is_extreme[global_positions] = 1
            extreme_type[global_positions] = extreme_name
            episodes.append(
                {
                    "extreme_type": extreme_name,
                    "station_id": station_id,
                    "start": str(timestamps.iloc[start]),
                    "end": str(timestamps.iloc[min(start + duration - 1, len(timestamps) - 1)]),
                    "duration_hours": int(duration),
                }
            )

            if rng.random() < 0.5:
                partner_id = neighbour_station(station_id, rng)
                partner_mask = working_frame["station_id"] == partner_id
                partner_positions = np.flatnonzero(partner_mask.to_numpy())
                if len(partner_positions) == 0:
                    continue
                partner_slice = working_frame.iloc[partner_positions].copy()
                partner_timestamps = partner_slice["timestamp"].reset_index(drop=True)
                partner_start = candidate_starts(
                    partner_timestamps,
                    SEASON_MONTHS[extreme_name],
                    duration,
                    rng,
                    fallback_all=True,
                )
                if partner_start is None:
                    continue
                partner_local = partner_slice[list(config.SENSORS)].reset_index(drop=True)
                partner_local = clip_to_physical_bounds(partner_local)
                partner_local = applier(partner_local, partner_start, duration, rng)
                partner_local = clip_to_physical_bounds(partner_local)
                partner_globals = partner_positions[partner_start:partner_start + duration]
                working_frame.loc[partner_globals, list(config.SENSORS)] = partner_local.iloc[
                    partner_start:partner_start + duration
                ].to_numpy()
                is_extreme[partner_globals] = 1
                extreme_type[partner_globals] = extreme_name
                episodes.append(
                    {
                        "extreme_type": extreme_name,
                        "station_id": partner_id,
                        "start": str(partner_timestamps.iloc[partner_start]),
                        "end": str(
                            partner_timestamps.iloc[
                                min(partner_start + duration - 1, len(partner_timestamps) - 1)
                            ]
                        ),
                        "duration_hours": int(duration),
                        "partner_of": station_id,
                    }
                )

    working_frame["is_extreme_event"] = is_extreme
    working_frame["extreme_type"] = extreme_type
    wide_result = working_frame.set_index(["station_id", "timestamp"]).sort_index()
    return wide_result, episodes
