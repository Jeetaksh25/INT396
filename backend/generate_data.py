import numpy as np
import pandas as pd
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
DATASET = ROOT / "data" / "processed" / "dataset.csv"
SEED = 42

STATIONS = {
    "DEL": ("Delhi", 28.61, 77.21),
    "BOM": ("Mumbai", 19.08, 72.88),
    "MAA": ("Chennai", 13.08, 80.27),
    "HYD": ("Hyderabad", 17.38, 78.48),
    "JAI": ("Jaipur", 26.92, 75.79),
    "CCU": ("Kolkata", 22.57, 88.36),
    "BLR": ("Bengaluru", 12.97, 77.59),
    "SLM": ("Shimla", 31.10, 77.17),
}
SENSORS = ["temperature", "humidity", "wind_speed", "pressure"]
UNITS = {"temperature": "C", "humidity": "%", "wind_speed": "km/h", "pressure": "hPa"}

FAULTS = {
    "bias": (24, 72),
    "drift": (72, 168),
    "stuck": (12, 48),
    "spike": (48, 96),
    "precision": (24, 96),
    "dropout": (6, 24),
}
EXTREMES = {
    "heat_wave": ([4, 5, 6], (72, 144), {"temperature": 11, "humidity": -22, "pressure": -5}),
    "cold_snap": ([12, 1, 2], (48, 120), {"temperature": -11, "wind_speed": 12, "humidity": 15}),
    "storm": ([6, 7, 8, 9, 10], (18, 36), {"wind_speed": 35, "pressure": -14, "humidity": 18}),
    "heavy_rain": ([6, 7, 8, 9], (12, 30), {"humidity": 28, "temperature": -6, "wind_speed": 16}),
}
FAULT_EPISODES = 5
EXTREME_EPISODES = 2

rng = np.random.default_rng(SEED)


def download(code):
    name, lat, lon = STATIONS[code]
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,pressure_msl",
        "timezone": "GMT",
    }
    hourly = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=60).json()["hourly"]
    frame = pd.DataFrame({
        "timestamp": hourly["time"],
        "temperature": hourly["temperature_2m"],
        "humidity": hourly["relative_humidity_2m"],
        "wind_speed": hourly["wind_speed_10m"],
        "pressure": hourly["pressure_msl"],
    })
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(RAW_DIR / f"{code}.csv", index=False)


def load_station(code):
    path = RAW_DIR / f"{code}.csv"
    if not path.exists():
        print("downloading", code)
        download(code)
    frame = pd.read_csv(path, parse_dates=["timestamp"])
    return frame.set_index("timestamp")[SENSORS].interpolate(limit=2).ffill().bfill()


def free_start(busy, month, months, length):
    for _ in range(2000):
        start = int(rng.integers(24, len(busy) - length - 24))
        if months and month[start] not in months:
            continue
        if not busy[start - 24:start + length + 24].any():
            busy[start:start + length] = True
            return start
    return None


def add_fault(kind, x, start, length, sd):
    part = x[start:start + length]
    hit = np.ones(length, dtype=bool)
    sign = rng.choice([-1, 1])
    if kind == "bias":
        part += sign * rng.uniform(4, 7) * sd
    elif kind == "drift":
        part += sign * np.linspace(1.5, rng.uniform(5, 8), length) * sd
    elif kind == "stuck":
        part[:] = part[0]
    elif kind == "spike":
        hit = rng.random(length) < 0.15
        part[hit] += rng.choice([-1, 1], hit.sum()) * rng.uniform(6, 10, hit.sum()) * sd
    elif kind == "precision":
        step = sd * rng.uniform(0.8, 1.5)
        part[:] = np.round(part / step) * step + rng.normal(0, step, length)
    elif kind == "dropout":
        part[:] = np.nan
    return hit


def build_station(code):
    clean = load_station(code)
    values = {s: clean[s].to_numpy(dtype=float).copy() for s in SENSORS}
    labels = {s: np.array(["normal"] * len(clean), dtype=object) for s in SENSORS}
    busy = np.zeros(len(clean), dtype=bool)
    month = clean.index.month.to_numpy()

    for kind, (months, (low, high), effect) in EXTREMES.items():
        for _ in range(EXTREME_EPISODES):
            length = int(rng.integers(low, high))
            start = free_start(busy, month, months, length)
            if start is None:
                continue
            shape = np.sin(np.pi * np.linspace(0, 1, length))
            strength = rng.uniform(0.8, 1.2)
            for sensor, size in effect.items():
                values[sensor][start:start + length] += size * strength * shape
                labels[sensor][start:start + length][shape > 0.3] = kind

    for kind, (low, high) in FAULTS.items():
        for _ in range(FAULT_EPISODES):
            length = int(rng.integers(low, high))
            start = free_start(busy, month, None, length)
            if start is None:
                continue
            sensor = SENSORS[rng.integers(len(SENSORS))]
            sd = clean[sensor].std()
            hit = add_fault(kind, values[sensor], start, length, sd)
            labels[sensor][start:start + length][hit] = kind

    rows = []
    for sensor in SENSORS:
        extreme = np.isin(labels[sensor], list(EXTREMES))
        measured = values[sensor].copy()
        if sensor == "humidity":
            measured[extreme] = np.clip(measured[extreme], 0, 100)
        if sensor == "wind_speed":
            measured[extreme] = np.clip(measured[extreme], 0, None)
        rows.append(pd.DataFrame({
            "station_id": code,
            "timestamp": clean.index,
            "sensor_name": sensor,
            "clean_value": clean[sensor].round(2).to_numpy(),
            "measured_value": np.round(measured, 2),
            "label": labels[sensor],
        }))
    return pd.concat(rows)


def label_group(label):
    if label in FAULTS:
        return "fault"
    if label in EXTREMES:
        return "extreme"
    return "normal"


if __name__ == "__main__":
    data = pd.concat([build_station(code) for code in STATIONS], ignore_index=True)
    data["group"] = data["label"].map(label_group)
    DATASET.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(DATASET, index=False)
    print(len(data), "rows saved to", DATASET)
    print(data["group"].value_counts(normalize=True).round(4))
    print(data["label"].value_counts())
