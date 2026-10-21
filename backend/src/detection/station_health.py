import json

import pandas as pd

import config


def build_health_status(fault_events, extreme_events, anomalous_percent):
    if fault_events > 0:
        return "FAULT"
    if extreme_events > 0:
        return "EXTREME_EVENT"
    if anomalous_percent > config.WATCH_ANOMALY_PERCENT:
        return "WATCH"
    return "HEALTHY"


def build_station_health(labelled_detections, events_frame):
    latest_timestamp = labelled_detections["timestamp"].max()
    window_start = latest_timestamp - pd.Timedelta(hours=config.STATION_HEALTH_WINDOW_HOURS)

    health_rows = []
    for station_id, station in config.STATION_REGISTRY.items():
        station_rows = labelled_detections[labelled_detections["station_id"] == station_id]
        window_rows = station_rows[station_rows["timestamp"] >= window_start]
        station_events = events_frame[events_frame["station_id"] == station_id]
        window_events = station_events[
            (station_events["end"] >= window_start) | (station_events["start"] >= window_start)
        ]

        fault_events = int((window_events["label"] == "FAULT").sum())
        extreme_events = int((window_events["label"] == "EXTREME").sum())
        anomalous_percent = round(100.0 * float(window_rows["is_anomaly"].mean()), 2) if len(window_rows) else 0.0
        last_fault = station_events[station_events["label"] == "FAULT"].sort_values("end")

        health_rows.append(
            {
                "station_id": station_id,
                "station_name": station["name"],
                "latitude": station["latitude"],
                "longitude": station["longitude"],
                "status": build_health_status(fault_events, extreme_events, anomalous_percent),
                "fault_events": fault_events,
                "extreme_events": extreme_events,
                "anomalous_percent": anomalous_percent,
                "last_reading_at": str(latest_timestamp),
                "last_fault_type": (
                    str(last_fault["reason_code"].iloc[-1]) if len(last_fault) else None
                ),
                "total_events": int(len(station_events)),
                "window_hours": config.STATION_HEALTH_WINDOW_HOURS,
            }
        )
    return health_rows


def save_station_health(health_rows):
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.STATION_HEALTH_JSON, "w", encoding="utf-8") as handle:
        json.dump(health_rows, handle, indent=2)
    return health_rows
