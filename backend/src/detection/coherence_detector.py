import numpy as np
import pandas as pd

import config

SMOOTH_WINDOW = 12

SUSTAINED_THRESHOLD = 1.15

REGIONAL_THRESHOLD = 0.55


def station_deviation_frame(features):
    return features.pivot_table(
        index=["station_id", "timestamp"],
        columns="sensor_name",
        values="climatology_deviation",
        aggfunc="max",
        fill_value=0.0,
    ).reindex(columns=list(config.SENSORS), fill_value=0.0)


def neighbour_share_frame(features):
    return features.pivot_table(
        index=["station_id", "timestamp"],
        columns="sensor_name",
        values="neighbour_share",
        aggfunc="max",
        fill_value=0.0,
    ).reindex(columns=list(config.SENSORS), fill_value=0.0)


def sustained_score(deviation_frame):
    station_mean = deviation_frame.mean(axis=1).reset_index()
    station_mean.columns = ["station_id", "timestamp", "deviation"]
    station_mean = station_mean.sort_values(["station_id", "timestamp"])

    smoothed = station_mean.groupby("station_id")["deviation"].transform(
        lambda series: series.rolling(SMOOTH_WINDOW, min_periods=max(2, SMOOTH_WINDOW // 3)).mean()
    )
    station_mean["sustained"] = smoothed.fillna(0.0)

    regional = station_mean.groupby("timestamp")["deviation"].transform("mean")
    station_mean["regional"] = regional.fillna(0.0)

    return station_mean


def score_coherence(features):
    deviation_frame = station_deviation_frame(features)
    neighbour_frame = neighbour_share_frame(features)
    station_mean = sustained_score(deviation_frame)

    sustained = (
        station_mean.set_index(["station_id", "timestamp"])["sustained"]
        .reindex(deviation_frame.index)
        .fillna(0.0)
    )
    regional = (
        station_mean.set_index(["station_id", "timestamp"])["regional"]
        .reindex(deviation_frame.index)
        .fillna(0.0)
    )

    multi_sensor = (deviation_frame > 0.9).sum(axis=1)
    neighbour = neighbour_frame.mean(axis=1)

    station_score = (
        0.45 * (sustained / SUSTAINED_THRESHOLD)
        + 0.30 * (multi_sensor / max(1.0, float(config.CONSENSUS_VOTE_TOTAL)))
        + 0.25 * (neighbour / max(1e-6, config.NEIGHBOUR_AGREEMENT_THRESHOLD))
    )

    lookup = station_score.to_dict()
    keys = list(zip(features["station_id"], pd.to_datetime(features["timestamp"])))
    values = np.array([lookup.get(key, 0.0) for key in keys], dtype=float)

    regional_keys = (np.array([key[1] for key in keys]),)
    regional_lookup = regional.to_dict()
    regional_values = np.array(
        [regional_lookup.get((key[0], key[1]), 0.0) for key in keys], dtype=float
    )

    combined = np.maximum(values, regional_values / max(1e-6, REGIONAL_THRESHOLD))
    return combined


def coherence_vote(features, reference_mask):
    scores = score_coherence(features)
    reference_scores = scores[reference_mask]
    if len(reference_scores) == 0:
        threshold = float(np.quantile(scores, config.REFERENCE_QUANTILE))
    else:
        threshold = float(np.quantile(scores, min(0.995, config.REFERENCE_QUANTILE)))
    vote = (scores > threshold).astype(int)
    return scores, vote, threshold
