import numpy as np
import pandas as pd

import config


def compute_sensor_coherence(group):
    sensor_names = group["sensor_name"].tolist()
    return len(set(sensor_names))


def is_single_sensor(group):
    return group["sensor_name"].nunique() == 1


def neighbour_agreement_for(event_rows, detection_frame):
    agreement_values = []
    station_id = event_rows["station_id"].iloc[0]
    sensor_name = event_rows["sensor_name"].iloc[0]
    start = event_rows["timestamp"].min()
    end = event_rows["timestamp"].max()

    other_stations = detection_frame[
        (detection_frame["station_id"] != station_id)
        & (detection_frame["sensor_name"] == sensor_name)
    ]
    neighbour_ids = other_stations["station_id"].unique()
    for neighbour_id in neighbour_ids:
        neighbour_window = other_stations[
            (other_stations["station_id"] == neighbour_id)
            & (other_stations["timestamp"] >= start)
            & (other_stations["timestamp"] <= end)
        ]
        if len(neighbour_window) == 0:
            continue
        agreement_values.append(float(neighbour_window["is_anomaly"].mean()))
    if not agreement_values:
        return 0.0
    return float(np.mean(agreement_values))


def physical_violation_score(event_rows, feature_frame):
    matching = feature_frame[
        (feature_frame["station_id"] == event_rows["station_id"].iloc[0])
        & (feature_frame["sensor_name"] == event_rows["sensor_name"].iloc[0])
        & (feature_frame["timestamp"] >= event_rows["timestamp"].min())
        & (feature_frame["timestamp"] <= event_rows["timestamp"].max())
    ]
    if len(matching) == 0:
        return 0.0
    return float((matching["rule_violation_count"] > 0).mean())


def sustained_hours(event_rows):
    return int(event_rows["timestamp"].nunique())


def classify_event(event_rows, detection_frame, feature_frame):
    sensor_count = event_rows["sensor_name"].nunique()
    neighbour_agreement = neighbour_agreement_for(event_rows, detection_frame)
    violation_rate = physical_violation_score(event_rows, feature_frame)
    duration = sustained_hours(event_rows)

    all_sensor_anomalies = detection_frame[
        (detection_frame["station_id"] == event_rows["station_id"].iloc[0])
        & (detection_frame["timestamp"] >= event_rows["timestamp"].min())
        & (detection_frame["timestamp"] <= event_rows["timestamp"].max())
        & (detection_frame["is_anomaly"] == 1)
    ]
    anomalous_sensor_count = all_sensor_anomalies["sensor_name"].nunique()
    coherent_across_sensors = anomalous_sensor_count >= 2

    if violation_rate > 0.5:
        return "FAULT", "physics_inconsistent", neighbour_agreement, coherent_across_sensors, duration
    if sensor_count == 1 and anomalous_sensor_count == 1 and neighbour_agreement < config.NEIGHBOUR_AGREEMENT_THRESHOLD:
        return "FAULT", "isolated_sensor", neighbour_agreement, coherent_across_sensors, duration
    if neighbour_agreement >= config.NEIGHBOUR_AGREEMENT_THRESHOLD and coherent_across_sensors:
        return "EXTREME", "regional_coherent", neighbour_agreement, coherent_across_sensors, duration
    if duration > config.SUSTAINED_EVENT_HOURS and neighbour_agreement >= config.NEIGHBOUR_AGREEMENT_THRESHOLD:
        return "EXTREME", "sustained_regime", neighbour_agreement, coherent_across_sensors, duration
    return "FAULT", "isolated_or_erratic", neighbour_agreement, coherent_across_sensors, duration


def group_anomaly_events(detection_frame):
    anomalies = detection_frame[detection_frame["is_anomaly"] == 1].copy()
    anomalies = anomalies.sort_values(["station_id", "sensor_name", "timestamp"])
    events = []
    for (station_id, sensor_name), group in anomalies.groupby(["station_id", "sensor_name"]):
        group = group.sort_values("timestamp").reset_index(drop=True)
        if len(group) == 0:
            continue
        time_gaps = group["timestamp"].diff()
        new_event = (time_gaps.isna()) | (time_gaps > pd.Timedelta(hours=2))
        group["event_group"] = new_event.cumsum()
        for group_number, event_rows in group.groupby("event_group"):
            events.append(event_rows.copy())
    return events


def classify_all_events(detection_frame, feature_frame):
    event_rows_list = group_anomaly_events(detection_frame)
    results = []
    for index, event_rows in enumerate(event_rows_list):
        label, reason_code, neighbour_agreement, coherent_across_sensors, duration = classify_event(
            event_rows, detection_frame, feature_frame
        )
        results.append(
            {
                "event_id": f"EVT-{index + 1:05d}",
                "station_id": str(event_rows["station_id"].iloc[0]),
                "sensor_name": str(event_rows["sensor_name"].iloc[0]),
                "start": event_rows["timestamp"].min(),
                "end": event_rows["timestamp"].max(),
                "duration_hours": int(duration),
                "label": label,
                "reason_code": reason_code,
                "mean_anomaly_score": float(event_rows["anomaly_score"].mean()),
                "max_anomaly_score": float(event_rows["anomaly_score"].max()),
                "neighbour_agreement": round(float(neighbour_agreement), 3),
                "coherent_across_sensors": bool(coherent_across_sensors),
                "reading_count": int(len(event_rows)),
            }
        )
    events_frame = pd.DataFrame(results)
    return events_frame


def apply_event_labels(detection_frame, events_frame):
    labelled = detection_frame.copy()
    labelled["event_label"] = None
    labelled["reason_code"] = None
    for row in events_frame.itertuples():
        mask = (
            (labelled["station_id"] == row.station_id)
            & (labelled["sensor_name"] == row.sensor_name)
            & (labelled["timestamp"] >= row.start)
            & (labelled["timestamp"] <= row.end)
        )
        labelled.loc[mask, "event_label"] = row.label
        labelled.loc[mask, "reason_code"] = row.reason_code
    labelled["is_fault_flagged"] = (
        (labelled["is_anomaly"] == 1) & (labelled["event_label"] == "FAULT")
    ).astype(int)
    labelled["is_extreme_flagged"] = (
        (labelled["is_anomaly"] == 1) & (labelled["event_label"] == "EXTREME")
    ).astype(int)
    return labelled
