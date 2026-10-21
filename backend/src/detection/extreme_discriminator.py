import numpy as np
import pandas as pd

import config


def build_context_tables(detections, feature_frame):
    anomaly_matrix = (
        detections.assign(flag=detections["is_anomaly"].astype(int))
        .pivot_table(
            index=["station_id", "timestamp"],
            columns="sensor_name",
            values="flag",
            aggfunc="max",
            fill_value=0,
        )
        .reindex(columns=config.SENSORS, fill_value=0)
    )
    anomaly_matrix["anomalous_sensor_count"] = anomaly_matrix.sum(axis=1)

    deviation_matrix = (
        detections.pivot_table(
            index=["station_id", "timestamp"],
            columns="sensor_name",
            values="sensor_deviation",
            aggfunc="first",
        )
        .reindex(columns=config.SENSORS)
    )

    neighbour_frames = []
    for sensor_name in config.SENSORS:
        wide = deviation_matrix[sensor_name].unstack(level="station_id")
        flagged = (wide > 1.5).astype(float)
        station_count = max(wide.shape[1] - 1, 1)
        others_flagged = flagged.sum(axis=1).to_numpy()[:, None] - flagged.to_numpy()
        agreement = pd.DataFrame(
            others_flagged / station_count,
            index=wide.index,
            columns=wide.columns,
        )
        stacked = agreement.stack()
        stacked.index.names = ["timestamp", "station_id"]
        frame = stacked.rename("neighbour_agreement").reset_index()
        frame["sensor_name"] = sensor_name
        neighbour_frames.append(frame)
    neighbour_agreement = pd.concat(neighbour_frames, ignore_index=True)

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
        ["station_id", "sensor_name", "timestamp", "is_anomaly", "anomaly_score"]
    ].copy()
    context = context.merge(
        anomaly_matrix[["anomalous_sensor_count"]].reset_index(),
        on=["station_id", "timestamp"],
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
    context[["neighbour_agreement", "physics_violation", "anomalous_sensor_count"]] = context[
        ["neighbour_agreement", "physics_violation", "anomalous_sensor_count"]
    ].fillna(0.0)
    return context


def assign_event_ids(context):
    flagged = context[context["is_anomaly"] == 1].copy()
    flagged = flagged.sort_values(["station_id", "sensor_name", "timestamp"]).reset_index(drop=True)
    time_gap = flagged.groupby(["station_id", "sensor_name"])["timestamp"].diff()
    new_event = time_gap.isna() | (time_gap > pd.Timedelta(hours=2))
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

    if physics > 0:
        return "FAULT", "physics_inconsistent", mean_neighbour, single_sensor, duration
    if single_sensor and mean_neighbour < config.NEIGHBOUR_AGREEMENT_THRESHOLD:
        return "FAULT", "isolated_sensor", mean_neighbour, single_sensor, duration
    if mean_neighbour >= config.NEIGHBOUR_AGREEMENT_THRESHOLD and not single_sensor:
        return "EXTREME", "regional_coherent", mean_neighbour, single_sensor, duration
    if duration > config.SUSTAINED_EVENT_HOURS and mean_neighbour >= config.NEIGHBOUR_AGREEMENT_THRESHOLD:
        return "EXTREME", "sustained_regime", mean_neighbour, single_sensor, duration
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
    labelled = detection_frame.copy()
    labelled["event_label"] = None
    labelled["reason_code"] = None

    if len(events_frame) == 0:
        labelled["is_fault_flagged"] = 0
        labelled["is_extreme_flagged"] = 0
        return labelled

    flagged = labelled[labelled["is_anomaly"] == 1].copy()
    flagged = flagged.sort_values(["station_id", "sensor_name", "timestamp"]).reset_index(drop=True)
    time_gap = flagged.groupby(["station_id", "sensor_name"])["timestamp"].diff()
    new_event = time_gap.isna() | (time_gap > pd.Timedelta(hours=2))
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
    mapped = flagged["event_id"].map(lookup["label"])
    mapped_reason = flagged["event_id"].map(lookup["reason_code"])

    labelled.loc[flagged.index, "event_label"] = mapped.to_numpy()
    labelled.loc[flagged.index, "reason_code"] = mapped_reason.to_numpy()
    labelled["is_fault_flagged"] = (
        (labelled["is_anomaly"] == 1) & (labelled["event_label"] == "FAULT")
    ).astype(int)
    labelled["is_extreme_flagged"] = (
        (labelled["is_anomaly"] == 1) & (labelled["event_label"] == "EXTREME")
    ).astype(int)
    return labelled
