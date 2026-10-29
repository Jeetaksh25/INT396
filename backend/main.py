import json
import queue
import threading

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from generate_data import STATIONS
from model import RESULTS
from simulation import run_simulation

DETECTIONS_CSV = RESULTS / "detections.csv"
EVENTS_CSV = RESULTS / "detection_events.csv"
STATION_HEALTH_JSON = RESULTS / "station_health.json"
METRICS_JSON = RESULTS / "metrics.json"

app = FastAPI(title="INT396 Sensor Fault Classifier API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_detection_cache = {}
_health_cache = {}
_metrics_cache = {}


def read_json(path):
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"missing results file: {path.name}")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_detections():
    modified = DETECTIONS_CSV.stat().st_mtime if DETECTIONS_CSV.exists() else 0
    if _detection_cache.get("mtime") != modified:
        if not DETECTIONS_CSV.exists():
            raise HTTPException(status_code=503, detail="detections.csv not generated yet")
        frame = pd.read_csv(DETECTIONS_CSV, parse_dates=["timestamp"])
        _detection_cache["mtime"] = modified
        _detection_cache["frame"] = frame
    return _detection_cache["frame"]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/metrics")
def metrics():
    modified = METRICS_JSON.stat().st_mtime if METRICS_JSON.exists() else 0
    if _metrics_cache.get("mtime") != modified:
        _metrics_cache["mtime"] = modified
        _metrics_cache["data"] = read_json(METRICS_JSON)
    return _metrics_cache["data"]


@app.get("/api/stations")
def stations():
    modified = STATION_HEALTH_JSON.stat().st_mtime if STATION_HEALTH_JSON.exists() else 0
    if _health_cache.get("mtime") != modified:
        _health_cache["mtime"] = modified
        _health_cache["data"] = read_json(STATION_HEALTH_JSON)
    return _health_cache["data"]


@app.get("/api/stations/{station_id}")
def station_detail(station_id: str, hours: int = Query(default=168, ge=1, le=8760)):
    if station_id not in STATIONS:
        raise HTTPException(status_code=404, detail="unknown station")
    health_rows = stations()
    station_health = next(
        (row for row in health_rows if row["station_id"] == station_id), None
    )
    if station_health is None:
        raise HTTPException(status_code=404, detail="station health missing")

    frame = load_detections()
    station_rows = frame[frame["station_id"] == station_id]
    if len(station_rows) == 0:
        raise HTTPException(status_code=404, detail="no detections for station")

    latest = station_rows["timestamp"].max()
    window_start = latest - pd.Timedelta(hours=hours)
    window_rows = station_rows[station_rows["timestamp"] >= window_start].copy()

    sensor_summary = (
        window_rows.groupby("sensor_name")
        .agg(
            readings=("is_anomaly", "size"),
            anomalies=("is_anomaly", "sum"),
            fault_flags=("is_fault_flagged", "sum"),
            extreme_flags=("is_extreme_flagged", "sum"),
            mean_value=("measured_value", "mean"),
            max_score=("anomaly_score", "max"),
        )
        .reset_index()
    )
    for column in ["mean_value", "max_score"]:
        sensor_summary[column] = sensor_summary[column].round(3)

    fault_breakdown = (
        window_rows[window_rows["is_fault_flagged"] == 1]
        .groupby("reason_code")
        .size()
        .reset_index(name="count")
        .to_dict(orient="records")
    )

    recent = window_rows[window_rows["is_anomaly"] == 1].sort_values(
        "anomaly_score", ascending=False
    ).head(25)

    return {
        "station": station_health,
        "hours": hours,
        "window_start": str(window_start),
        "window_end": str(latest),
        "sensor_summary": sensor_summary.to_dict(orient="records"),
        "fault_breakdown": fault_breakdown,
        "recent_detections": [
            {
                "timestamp": str(row.timestamp),
                "sensor_name": row.sensor_name,
                "measured_value": None if pd.isna(row.measured_value) else float(row.measured_value),
                "anomaly_score": float(row.anomaly_score),
                "event_label": None if pd.isna(row.event_label) else str(row.event_label),
                "reason_code": None if pd.isna(row.reason_code) else str(row.reason_code),
            }
            for row in recent.itertuples()
        ],
    }


@app.get("/api/stations/{station_id}/series")
def station_series(station_id: str, days: int = Query(default=30, ge=1, le=365)):
    if station_id not in STATIONS:
        raise HTTPException(status_code=404, detail="unknown station")

    frame = load_detections()
    station_rows = frame[frame["station_id"] == station_id].copy()
    if len(station_rows) == 0:
        raise HTTPException(status_code=404, detail="no detections for station")

    latest = station_rows["timestamp"].max()
    start = latest - pd.Timedelta(days=days)
    window_rows = station_rows[station_rows["timestamp"] >= start].sort_values("timestamp")

    series = {}
    for sensor_name, group in window_rows.groupby("sensor_name"):
        series[sensor_name] = {
            "timestamps": [str(value) for value in group["timestamp"]],
            "values": [
                None if pd.isna(value) else round(float(value), 3)
                for value in group["measured_value"]
            ],
            "anomaly_scores": [round(float(value), 4) for value in group["anomaly_score"]],
            "is_anomaly": [int(value) for value in group["is_anomaly"]],
            "event_label": [None if pd.isna(value) else str(value) for value in group["event_label"]],
            "baseline_flag": [int(value) for value in group["baseline_flag"]],
        }

    events_path = EVENTS_CSV
    events = []
    if events_path.exists():
        events_frame = pd.read_csv(events_path, parse_dates=["start", "end"])
        station_events = events_frame[
            (events_frame["station_id"] == station_id) & (events_frame["end"] >= start)
        ]
        events = [
            {
                "event_id": str(row.event_id),
                "sensor_name": str(row.sensor_name),
                "start": str(row.start),
                "end": str(row.end),
                "label": str(row.label),
                "reason_code": str(row.reason_code),
                "mean_anomaly_score": round(float(row.mean_anomaly_score), 4),
            }
            for row in station_events.itertuples()
        ]

    return {
        "station_id": station_id,
        "days": days,
        "start": str(start),
        "end": str(latest),
        "series": series,
        "events": events,
    }


@app.get("/api/timeline")
def network_timeline(days: int = Query(default=30, ge=1, le=365)):
    frame = load_detections()
    latest = frame["timestamp"].max()
    start = latest - pd.Timedelta(days=days)
    window = frame[frame["timestamp"] >= start]

    grouped = (
        window.groupby("timestamp")
        .agg(
            anomalies=("is_anomaly", "sum"),
            fault_flags=("is_fault_flagged", "sum"),
            extreme_flags=("is_extreme_flagged", "sum"),
            readings=("is_anomaly", "size"),
        )
        .reset_index()
        .sort_values("timestamp")
    )
    grouped["anomaly_percent"] = (100.0 * grouped["anomalies"] / grouped["readings"]).round(3)
    return {
        "days": days,
        "start": str(start),
        "end": str(latest),
        "points": [
            {
                "timestamp": str(row.timestamp),
                "anomalies": int(row.anomalies),
                "fault_flags": int(row.fault_flags),
                "extreme_flags": int(row.extreme_flags),
                "anomaly_percent": float(row.anomaly_percent),
            }
            for row in grouped.itertuples()
        ],
    }


@app.get("/api/events")
def events(
    label: str | None = Query(default=None),
    station_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
):
    if not EVENTS_CSV.exists():
        raise HTTPException(status_code=503, detail="events not generated yet")
    frame = pd.read_csv(EVENTS_CSV, parse_dates=["start", "end"])
    if label:
        frame = frame[frame["label"].str.upper() == label.upper()]
    if station_id:
        frame = frame[frame["station_id"] == station_id]
    frame = frame.sort_values("start", ascending=False).head(limit)
    return {
        "count": int(len(frame)),
        "events": [
            {
                "event_id": str(row.event_id),
                "station_id": str(row.station_id),
                "sensor_name": str(row.sensor_name),
                "start": str(row.start),
                "end": str(row.end),
                "duration_hours": int(row.duration_hours),
                "label": str(row.label),
                "reason_code": str(row.reason_code),
                "mean_anomaly_score": round(float(row.mean_anomaly_score), 4),
                "neighbour_agreement": float(row.neighbour_agreement),
            }
            for row in frame.itertuples()
        ],
    }


@app.get("/api/model")
def model_card():
    return metrics()


@app.get("/api/simulation/events")
def simulation_events(
    seed: int = Query(default=1, ge=0, le=999999),
    profile: str = Query(default="balanced"),
):
    channel = queue.Queue()

    def emit(phase, fraction, detail):
        channel.put({"phase": phase, "fraction": round(float(fraction), 3), "detail": detail})

    def worker():
        try:
            summary = run_simulation(seed or 1, progress=emit, operating_point=profile)
            channel.put({"phase": "complete", "fraction": 1.0, "result": summary})
        except Exception as error:
            channel.put({"phase": "failed", "fraction": 1.0, "detail": str(error)})
        finally:
            channel.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            item = channel.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, default=str)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
