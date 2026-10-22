import numpy as np
import pandas as pd

import config


def build_context_tables(detections, feature_frame):
    anomaly_matrix = (
        detections.pivot_table(
            index=["station_id", "timestamp"],
            columns="sensor_name",
            values="is_local_anomaly",
            aggfunc="max",
            fill_value=0,
        )
        .reindex(columns=config.SENSORS, fill_value=0)
    )
    anomaly_matrix["anomalous_sensor_count"] = anomaly_matrix.sum(axis=1)

    extreme_matrix = (
        feature_frame.pivot_table(
            index=["station_id", "timestamp"],
            columns="sensor_name",
            values="climatology_deviation",
            aggfunc="max",
            fill_value=0,
        )
        .reindex(columns=config.SENSORS, fill_value=0)
    )
    loud = (extreme_matrix > config.COHERENCE_SENSOR_THRESHOLD).sum(axis=1)
    extreme_matrix["coherent_sensor_count"] = loud.astype(float)

    neighbour_matrix = (
        feature_frame.pivot_table(
            index=["station_id", "timestamp"],
            columns="sensor_name",
            values="neighbour_share",
            aggfunc="max",
            fill_value=0,
        )
        .reindex(columns=config.SENSORS, fill_value=0)
    )

    other_matrix = (
        feature_frame.pivot_table(
            index=["station_id", "timestamp"],
            columns="sensor_name",
            values="other_sensor_deviation",
            aggfunc="max",
            fill_value=0,
        )
        .reindex(columns=config.SENSORS, fill_value=0)
    )

    neighbour_agreement = neighbour_matrix.stack().rename("neighbour_agreement").reset_index()
    neighbour_agreement.columns = [
        "station_id",
        "timestamp",
        "sensor_name",
        "neighbour_agreement",
    ]

    physics_matrix = (
        feature_frame.pivot_table(
            index=["station_id", "timestamp"],
            columns="sensor_name",
            values="physics_violation_count",
            aggfunc="max",
            fill_value=0,
        )
        .reindex(columns=config.SENSORS, fill_value=0)
        .max(axis=1)
    )

    context = detections[
        [
            "station_id",
            "sensor_name",
            "timestamp",
            "is_anomaly",
            "is_local_anomaly",
            "anomaly_score",
            "coherent_weather",
        ]
    ].copy()
    context = context.merge(
        feature_frame[
            ["station_id", "sensor_name", "timestamp", "climatology_deviation"]
        ].rename(columns={"climatology_deviation": "sensor_deviation"}),
        on=["station_id", "sensor_name", "timestamp"],
        how="left",
    )
    context["sensor_deviation"] = context["sensor_deviation"].fillna(0.0)
    context = context.merge(
        anomaly_matrix[["anomalous_sensor_count"]].reset_index(),
        on=["station_id", "timestamp"],
        how="left",
    )
    context = context.merge(
        extreme_matrix[["coherent_sensor_count"]].reset_index(),
        on=["station_id", "timestamp"],
        how="left",
    )
    other_stacked = other_matrix.stack().rename("other_sensor_deviation").reset_index()
    other_stacked.columns = ["station_id", "timestamp", "sensor_name", "other_sensor_deviation"]
    context = context.merge(
        other_stacked,
        on=["station_id", "timestamp", "sensor_name"],
        how="left",
    )
    context = context.merge(
        neighbour_agreement.reset_index(),
        on=["station_id", "sensor_name", "timestamp"],
        how="left",
    )
    context = context.merge(
        physics_matrix.rename("physics_violation").reset_index(),
        on=["station_id", "timestamp"],
        how="left",
    )
    context[
        [
            "neighbour_agreement",
            "physics_violation",
            "anomalous_sensor_count",
            "coherent_sensor_count",
            "other_sensor_deviation",
        ]
    ] = context[
        [
            "neighbour_agreement",
            "physics_violation",
            "anomalous_sensor_count",
            "coherent_sensor_count",
            "other_sensor_deviation",
        ]
    ].fillna(0.0)
    return context


def assign_event_ids(context):
    station_loud = context.groupby(["station_id", "timestamp"])["sensor_deviation"].transform(
        "max"
    )
    context = context.copy()
    context["station_max_deviation"] = station_loud.fillna(0.0)
    flagged = context[
        (context["is_local_anomaly"] == 1) | (context["coherent_weather"] == 1)
    ].copy()
    flagged = flagged.sort_values(["station_id", "sensor_name", "timestamp"]).reset_index(drop=True)
    time_gap = flagged.groupby(["station_id", "sensor_name"])["timestamp"].diff()
    new_event = time_gap.isna() | (time_gap > pd.Timedelta(hours=config.EVENT_MERGE_GAP_HOURS))
    flagged["event_number"] = new_event.groupby(
        [flagged["station_id"], flagged["sensor_name"]]
    ).cumsum()
    flagged["event_id"] = (
        flagged["station_id"].astype(str)
        + "-"
        + flagged["sensor_name"].astype(str)
        + "-"
        + flagged["event_number"].astype(int).astype(str)
    )
    return flagged


def classify_group(group):
    mean_neighbour = float(group["neighbour_agreement"].mean())
    physics = float(group["physics_violation"].max())
    duration = int(group["timestamp"].nunique())
    sensors_flagged = int(group["anomalous_sensor_count"].max())
    single_sensor = sensors_flagged <= 1

    own_deviation = float(group["sensor_deviation"].median())
    other_deviation = float(group["other_sensor_deviation"].median())
    coherence_ratio = other_deviation / (own_deviation + 1e-6)
    coherent = (
        other_deviation >= config.COHERENT_OTHER_DEVIATION
        and coherence_ratio >= config.COHERENCE_RATIO_THRESHOLD
    )
    regional = mean_neighbour >= config.NEIGHBOUR_AGREEMENT_THRESHOLD
    sensors_loud = int(group["coherent_sensor_count"].max())
    if physics > 0 and sensors_loud < config.COHERENCE_SENSOR_COUNT:
        return "FAULT", "physics_inconsistent", mean_neighbour, single_sensor, duration
    if sensors_loud >= config.COHERENCE_SENSOR_COUNT:
        if regional:
            return "EXTREME", "coherent_regional", mean_neighbour, single_sensor, duration
        return "EXTREME", "coherent_multi_sensor", mean_neighbour, single_sensor, duration
    if coherent and (regional or duration >= config.SUSTAINED_EVENT_HOURS):
        return "EXTREME", "coherent_regional", mean_neighbour, single_sensor, duration
    if coherent:
        return "EXTREME", "coherent_multi_sensor", mean_neighbour, single_sensor, duration
    if single_sensor:
        return "FAULT", "isolated_sensor", mean_neighbour, single_sensor, duration
    return "FAULT", "isolated_or_erratic", mean_neighbour, single_sensor, duration


def classify_all_events(detections, feature_frame):
    context = build_context_tables(detections, feature_frame)
    flagged = assign_event_ids(context)

    rows = []
    grouped = flagged.groupby("event_id", sort=False)
    for event_id, group in grouped:
        label, reason, neighbour, single_sensor, duration = classify_group(group)
        rows.append(
            {
                "event_id": event_id,
                "station_id": str(group["station_id"].iloc[0]),
                "sensor_name": str(group["sensor_name"].iloc[0]),
                "start": group["timestamp"].min(),
                "end": group["timestamp"].max(),
                "duration_hours": duration,
                "label": label,
                "reason_code": reason,
                "mean_anomaly_score": float(group["anomaly_score"].mean()),
                "max_anomaly_score": float(group["anomaly_score"].max()),
                "neighbour_agreement": round(neighbour, 3),
                "single_sensor": bool(single_sensor),
                "reading_count": int(len(group)),
            }
        )
    return pd.DataFrame(rows)


def apply_event_labels(detection_frame, events_frame):
    labelled = detection_frame.copy().reset_index(drop=True)
    label_values = np.full(len(labelled), None, dtype=object)
    reason_values = np.full(len(labelled), None, dtype=object)

    if len(events_frame) == 0:
        labelled["event_label"] = label_values
        labelled["reason_code"] = reason_values
        labelled["is_fault_flagged"] = np.zeros(len(labelled), dtype=int)
        labelled["is_extreme_flagged"] = np.zeros(len(labelled), dtype=int)
        return labelled

    station_loud = labelled.groupby(["station_id", "timestamp"])["sensor_deviation"].transform(
        "max"
    )
    labelled = labelled.copy()
    labelled["station_max_deviation"] = station_loud.fillna(0.0)
    flagged = labelled[
        (labelled["is_local_anomaly"] == 1) | (labelled["coherent_weather"] == 1)
    ].copy()
    flagged = flagged.sort_values(["station_id", "sensor_name", "timestamp"]).reset_index(drop=False)
    time_gap = flagged.groupby(["station_id", "sensor_name"])["timestamp"].diff()
    new_event = time_gap.isna() | (time_gap > pd.Timedelta(hours=config.EVENT_MERGE_GAP_HOURS))
    flagged["event_number"] = new_event.groupby(
        [flagged["station_id"], flagged["sensor_name"]]
    ).cumsum()
    flagged["event_id"] = (
        flagged["station_id"].astype(str)
        + "-"
        + flagged["sensor_name"].astype(str)
        + "-"
        + flagged["event_number"].astype(int).astype(str)
    )

    lookup = events_frame.set_index("event_id")[["label", "reason_code"]]
    labels = flagged["event_id"].map(lookup["label"]).to_numpy()
    reasons = flagged["event_id"].map(lookup["reason_code"]).to_numpy()
    positions = flagged["index"].to_numpy()

    label_values[positions] = labels
    reason_values[positions] = reasons

    labelled["event_label"] = label_values
    labelled["reason_code"] = reason_values
    labelled["is_fault_flagged"] = (labelled["event_label"] == "FAULT").astype(int)
    labelled["is_extreme_flagged"] = (labelled["event_label"] == "EXTREME").astype(int)
    return labelled
