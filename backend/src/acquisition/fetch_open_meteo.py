import io
import json
import time

import pandas as pd
import requests

import config

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_station(station_id, latitude, longitude, start_date, end_date, retries=4):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(config.SOURCE_VARIABLES.values()),
        "timezone": "UTC",
        "format": "json",
    }
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(ARCHIVE_URL, params=params, timeout=180)
            response.raise_for_status()
            payload = response.json()
            hourly = payload["hourly"]
            frame = pd.DataFrame({"timestamp": pd.to_datetime(hourly["time"])})
            for sensor_name, source_name in config.SOURCE_VARIABLES.items():
                frame[sensor_name] = hourly[source_name]
            frame["station_id"] = station_id
            return frame
        except Exception as error:
            last_error = error
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"could not fetch {station_id}: {last_error}")


def fetch_all_stations(start_date=config.START_DATE, end_date=config.END_DATE):
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for station_id, station in config.STATION_REGISTRY.items():
        frame = fetch_station(
            station_id,
            station["latitude"],
            station["longitude"],
            start_date,
            end_date,
        )
        target_path = config.RAW_DIR / f"{station_id}.csv"
        frame.to_csv(target_path, index=False)
        metadata = {
            "station_id": station_id,
            "station_name": station["name"],
            "latitude": station["latitude"],
            "longitude": station["longitude"],
            "rows": len(frame),
            "start": str(frame["timestamp"].min()),
            "end": str(frame["timestamp"].max()),
            "source": "Open-Meteo Historical Weather API (ERA5)",
        }
        with open(config.RAW_DIR / f"{station_id}.json", "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)
        saved_paths.append(target_path)
        print(f"fetched {station_id} {station['name']}: {len(frame)} rows")
    return saved_paths


if __name__ == "__main__":
    fetch_all_stations()
