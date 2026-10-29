import json
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

from booster import TREES, boost
from generate_data import DATASET, EXTREMES, FAULTS, ROOT, SENSORS, STATIONS, label_group

RESULTS = ROOT / "results"
FEATURES = [
    "value_z", "dev_day", "dev_week", "jump", "noise_6h", "noise_day", "flat_6h", "missing_6h",
    "others_dev", "others_week", "temp_week", "humid_week", "wind_week", "press_week", "sensor_code", "hour",
]
UNSUPERVISED_FEATURES = FEATURES[:-2]
LIMITS = {"temperature": (-5, 45), "humidity": (0, 100), "wind_speed": (0, 120), "pressure": (950, 1050)}
CLASSES = ["normal"] + list(FAULTS) + list(EXTREMES)
DETECTORS = ["isolation", "lof", "kmeans", "pca"]
SAMPLE = 20000
VOTE_QUANTILE = 0.95
VOTES_NEEDED = 2
COHERENCE = 0.5


def series_features(values):
    missing = values.isna().astype(int)
    v = values.ffill().bfill()
    sd = v.std()
    day = v.rolling(24, center=True, min_periods=1).median()
    fortnight = v.rolling(336, center=True, min_periods=1).median()
    step = v.diff().fillna(0)
    return pd.DataFrame({
        "value_z": (v - v.mean()) / sd,
        "dev_day": (v - day) / sd,
        "dev_week": (day - fortnight) / sd,
        "jump": step / sd,
        "noise_6h": step.rolling(6, center=True, min_periods=1).std().fillna(0) / sd,
        "noise_day": step.rolling(24, center=True, min_periods=1).std().fillna(0) / sd,
        "flat_6h": (step.abs() < 1e-9).astype(int).rolling(6, center=True, min_periods=1).sum(),
        "missing_6h": missing.rolling(6, center=True, min_periods=1).sum(),
    }, index=values.index)


def build_features(data):
    data = data.sort_values(["station_id", "sensor_name", "timestamp"]).reset_index(drop=True)
    parts = [series_features(group["measured_value"]) for _, group in data.groupby(["station_id", "sensor_name"], sort=False)]
    data = data.join(pd.concat(parts))
    data["size_day"] = data["dev_day"].abs()
    data["size_week"] = data["dev_week"].abs()
    station_total = data.groupby(["station_id", "timestamp"])[["size_day", "size_week"]].transform("sum")
    data["others_dev"] = (station_total["size_day"] - data["size_day"]) / 3
    data["others_week"] = (station_total["size_week"] - data["size_week"]) / 3
    wide = data.pivot_table(index=["station_id", "timestamp"], columns="sensor_name", values="dev_week")
    wide.columns = [{"temperature": "temp_week", "humidity": "humid_week", "wind_speed": "wind_week", "pressure": "press_week"}[c] for c in wide.columns]
    data = data.join(wide, on=["station_id", "timestamp"])
    data["sensor_code"] = data["sensor_name"].map({s: i for i, s in enumerate(SENSORS)})
    data["hour"] = data["timestamp"].dt.hour
    return data.drop(columns=["size_day", "size_week"])


def range_check(data):
    low = data["sensor_name"].map(lambda s: LIMITS[s][0])
    high = data["sensor_name"].map(lambda s: LIMITS[s][1])
    value = data["measured_value"]
    return (value.isna() | (value < low) | (value > high)).astype(int)


def detector_scores(X):
    scaled = StandardScaler().fit_transform(X)
    rng = np.random.default_rng(42)
    sample = scaled[rng.choice(len(scaled), SAMPLE, replace=False)]
    iso = IsolationForest(n_estimators=200, random_state=42, n_jobs=-1).fit(sample)
    lof = LocalOutlierFactor(n_neighbors=20, novelty=True, n_jobs=-1).fit(sample)
    kmeans = KMeans(n_clusters=8, n_init=5, random_state=42).fit(sample)
    pca = PCA(n_components=0.9, random_state=42).fit(sample)
    rebuilt = pca.inverse_transform(pca.transform(scaled))
    found = {
        "isolation": -iso.score_samples(scaled),
        "lof": -lof.score_samples(scaled),
        "kmeans": kmeans.transform(scaled).min(axis=1),
        "pca": ((scaled - rebuilt) ** 2).sum(axis=1),
    }
    info = {"pca_components": int(pca.n_components_), "kmeans_clusters": 8, "lof_neighbours": 20, "isolation_trees": 200}
    return pd.DataFrame(found), info


def unsupervised(data):
    found, info = detector_scores(data[UNSUPERVISED_FEATURES])
    for name in DETECTORS:
        data[name] = found[name].to_numpy()
        data[name + "_vote"] = (data[name] > data[name].quantile(VOTE_QUANTILE)).astype(int)
    data["votes"] = data[[name + "_vote" for name in DETECTORS]].sum(axis=1)
    data["unsupervised_score"] = data[DETECTORS].rank(pct=True).mean(axis=1)
    flagged = data["votes"] >= VOTES_NEEDED
    data["unsupervised_group"] = np.where(~flagged, "normal", np.where(data["others_week"] > COHERENCE, "extreme", "fault"))
    return info


def scores(true, pred):
    return {
        "accuracy": round(accuracy_score(true, pred), 4),
        "balanced_accuracy": round(balanced_accuracy_score(true, pred), 4),
        "macro_f1": round(f1_score(true, pred, average="macro"), 4),
    }


def make_events(data):
    flagged = data[data["predicted_group"] != "normal"].sort_values(["station_id", "sensor_name", "timestamp"])
    events = []
    for (station, sensor), group in flagged.groupby(["station_id", "sensor_name"]):
        gap = group["timestamp"].diff() > pd.Timedelta(hours=3)
        changed = group["predicted_group"] != group["predicted_group"].shift()
        for number, (_, event) in enumerate(group.groupby((gap | changed).cumsum()), 1):
            start, end = event["timestamp"].min(), event["timestamp"].max()
            events.append({
                "event_id": f"{station}-{sensor}-{number}",
                "station_id": station,
                "sensor_name": sensor,
                "start": start,
                "end": end,
                "duration_hours": int((end - start) / pd.Timedelta(hours=1)) + 1,
                "label": event["predicted_group"].iloc[0].upper(),
                "reason_code": event["predicted_label"].mode().iloc[0],
                "true_label": event["label"].mode().iloc[0],
                "mean_anomaly_score": round(event["anomaly_score"].mean(), 4),
                "max_anomaly_score": round(event["anomaly_score"].max(), 4),
                "neighbour_agreement": round((event["others_dev"] > 1).mean(), 3),
                "reading_count": len(event),
            })
    return pd.DataFrame(events)


def station_health(data, events, window=720):
    latest = data["timestamp"].max()
    since = latest - pd.Timedelta(hours=window)
    rows = []
    for code, (name, lat, lon) in STATIONS.items():
        recent = data[(data["station_id"] == code) & (data["timestamp"] >= since)]
        mine = events[(events["station_id"] == code) & (events["end"] >= since)]
        faults = mine[mine["label"] == "FAULT"]
        extremes = mine[mine["label"] == "EXTREME"]
        percent = round(100 * (recent["predicted_group"] != "normal").mean(), 2)
        status = "FAULT" if len(faults) else "EXTREME_EVENT" if len(extremes) else "WATCH" if percent > 5 else "HEALTHY"
        all_faults = events[(events["station_id"] == code) & (events["label"] == "FAULT")]
        rows.append({
            "station_id": code,
            "station_name": name,
            "latitude": lat,
            "longitude": lon,
            "status": status,
            "fault_events": len(faults),
            "extreme_events": len(extremes),
            "anomalous_percent": percent,
            "last_reading_at": str(latest),
            "last_fault_type": None if all_faults.empty else all_faults.sort_values("end")["reason_code"].iloc[-1],
            "total_events": int((events["station_id"] == code).sum()),
            "window_hours": window,
        })
    return rows


def train():
    started = time.time()
    data = pd.read_csv(DATASET, parse_dates=["timestamp"])
    data = build_features(data)
    feature_seconds = time.time() - started

    detector_info = unsupervised(data)
    data["baseline_flag"] = range_check(data)
    unsupervised_seconds = time.time() - started - feature_seconds
    groups = ["normal", "fault", "extreme"]
    first = scores(data["group"], data["unsupervised_group"])
    first_matrix = confusion_matrix(data["group"], data["unsupervised_group"], labels=groups)
    print("unsupervised", first)

    RESULTS.mkdir(exist_ok=True)
    inputs = FEATURES + DETECTORS + ["votes"]
    y = data["label"]
    data["predicted_label"], data["anomaly_score"], model = boost(data[inputs], y, data["station_id"], RESULTS / "model.joblib")
    data["predicted_group"] = data["predicted_label"].map(label_group)
    order = sorted(y.unique())
    cv_seconds = time.time() - started - feature_seconds - unsupervised_seconds

    labels = [c for c in CLASSES if c in order]
    precision, recall, f1, support = precision_recall_fscore_support(y, data["predicted_label"], labels=labels, zero_division=0)
    group_matrix = confusion_matrix(data["group"], data["predicted_group"], labels=groups)
    baseline_group = np.where(data["baseline_flag"] == 1, "fault", "normal")
    per_station = {}
    for code in STATIONS:
        part = data[data["station_id"] == code]
        per_station[code] = scores(part["group"], part["predicted_group"])
    importance = sorted(zip(inputs, model.feature_importances_), key=lambda pair: -pair[1])

    events = make_events(data)
    flagged = data["predicted_group"] != "normal"
    data["is_anomaly"] = flagged.astype(int)
    data["is_fault_flagged"] = (data["predicted_group"] == "fault").astype(int)
    data["is_extreme_flagged"] = (data["predicted_group"] == "extreme").astype(int)
    data["event_label"] = data["predicted_group"].str.upper().where(flagged)
    data["reason_code"] = data["predicted_label"].where(flagged)
    data["anomaly_score"] = data["anomaly_score"].round(4)
    data["unsupervised_score"] = data["unsupervised_score"].round(4)
    keep = ["station_id", "sensor_name", "timestamp", "measured_value", "clean_value", "label", "predicted_label",
            "unsupervised_group", "unsupervised_score", "votes", "anomaly_score", "is_anomaly", "event_label", "reason_code", "is_fault_flagged", "is_extreme_flagged", "baseline_flag"]
    data[keep].to_csv(RESULTS / "detections.csv", index=False)
    events.to_csv(RESULTS / "detection_events.csv", index=False)
    with open(RESULTS / "station_health.json", "w") as f:
        json.dump(station_health(data, events), f, indent=2)

    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": "Unsupervised detection of faulty weather-station sensors, separated from genuine weather extremes, with a small supervised booster that refines the verdicts",
        "unsupervised": {
            "detectors": DETECTORS,
            "fit_sample": SAMPLE,
            "vote_quantile": VOTE_QUANTILE,
            "votes_needed": VOTES_NEEDED,
            "coherence_threshold": COHERENCE,
            **detector_info,
            "vote_rates": {name: round(float(data[name + "_vote"].mean()), 4) for name in DETECTORS},
            "flag_rate": round(float((data["votes"] >= VOTES_NEEDED).mean()), 4),
            "grouped": first,
            "group_confusion": {"labels": groups, "matrix": first_matrix.tolist()},
        },
        "model": {
            "name": "Random Forest booster",
            "trees": TREES,
            "min_samples_leaf": 2,
            "max_depth": 20,
            "why": "Takes the unsupervised detector scores and votes as extra inputs, learns from injected labels which flags are real faults or extremes, and shows which inputs mattered",
        },
        "evaluation": "4-fold GroupKFold by station: every reading is predicted by a model that never saw its station",
        "random_seed": 42,
        "dataset": {
            "stations": list(STATIONS),
            "sensors": SENSORS,
            "rows": len(data),
            "start": str(data["timestamp"].min()),
            "end": str(data["timestamp"].max()),
            "source": "Open-Meteo Historical Weather API (ERA5) with injected fault and extreme labels",
            "train_rows_per_fold": int(len(data) * 3 / 4),
            "test_rows_per_fold": int(len(data) / 4),
        },
        "label_counts": {"total_readings": len(data), **data["group"].value_counts().to_dict()},
        "class_counts": y.value_counts().to_dict(),
        "features": FEATURES,
        "detailed": scores(y, data["predicted_label"]),
        "grouped": scores(data["group"], data["predicted_group"]),
        "majority_baseline": round((data["group"] == "normal").mean(), 4),
        "range_check": scores(data["group"], baseline_group),
        "per_class": {
            label: {"precision": round(p, 4), "recall": round(r, 4), "f1": round(s, 4), "support": int(n)}
            for label, p, r, s, n in zip(labels, precision, recall, f1, support)
        },
        "group_confusion": {"labels": groups, "matrix": group_matrix.tolist()},
        "per_station": per_station,
        "feature_importance": {name: round(float(value), 4) for name, value in importance},
        "events": {
            "count": len(events),
            "fault_events": int((events["label"] == "FAULT").sum()),
            "extreme_events": int((events["label"] == "EXTREME").sum()),
            "correct_events": round(float((events["label"].str.lower() == events["true_label"].map(label_group)).mean()), 4),
        },
        "timing": {
            "features_seconds": round(feature_seconds, 1),
            "unsupervised_seconds": round(unsupervised_seconds, 1),
            "cross_validation_seconds": round(cv_seconds, 1),
            "total_seconds": round(time.time() - started, 1),
        },
    }
    with open(RESULTS / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("boosted", metrics["grouped"], "eleven classes", metrics["detailed"], "baseline", metrics["majority_baseline"])
    return metrics


if __name__ == "__main__":
    train()
