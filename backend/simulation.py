import time

import joblib
import numpy as np
import pandas as pd

import generate_data
from generate_data import EXTREMES, FAULTS, SENSORS, STATIONS, UNITS, label_group
from model import BOOSTER_INPUTS, DETECTORS, RESULTS, SAMPLE, VOTES_NEEDED, apply_votes, build_features, range_check

WINDOW_DAYS = 21
HISTORY_HOURS = 720
STREAM_SIZE = 96
PROFILES = {"balanced": None, "high_recall": 0.7, "high_precision": 0.25}
LANE = {"normal": "HEALTHY", "fault": "FAULT", "extreme": "EXTREME"}
TRUTH = {"normal": "clean", "fault": "fault", "extreme": "extreme"}

saved = {}


def load_models():
    if "booster" not in saved:
        saved["bank"] = joblib.load(RESULTS / "detectors.joblib")
        saved["booster"] = joblib.load(RESULTS / "model.joblib")
    return saved["bank"], saved["booster"]


def build_window(seed):
    generate_data.rng = np.random.default_rng(seed)
    hours = 8760
    window = WINDOW_DAYS * 24
    start = int(generate_data.rng.integers(HISTORY_HOURS, hours - window))
    busy = np.ones(hours, dtype=bool)
    busy[start:start + window] = False
    frames = []
    for code in STATIONS:
        kinds = [generate_data.rng.choice(list(EXTREMES))] if generate_data.rng.random() < 0.5 else []
        part = generate_data.build_station(code, busy=busy.copy(), fault_episodes=2, extreme_episodes=1, seasonal=False, extreme_kinds=kinds)
        times = np.sort(part["timestamp"].unique())
        frames.append(part[part["timestamp"].between(times[start - HISTORY_HOURS], times[start + window - 1])])
    data = pd.concat(frames, ignore_index=True)
    data["group"] = data["label"].map(label_group)
    return data, times[start]


def decide(proba, classes, profile):
    cut = PROFILES.get(profile)
    best = np.array(classes)[proba.argmax(axis=1)]
    if cut is None:
        return best
    normal = list(classes).index("normal")
    others = proba.copy()
    others[:, normal] = -1
    best_other = np.array(classes)[others.argmax(axis=1)]
    return np.where(proba[:, normal] < cut, best_other, "normal")


def rate(part, total):
    return round(float(part) / total, 4) if total else 0.0


def fault_block(truth, flagged, predicted):
    fault = truth == "fault"
    extreme = truth == "extreme"
    clean = truth == "normal"
    caught = (predicted == "fault") & fault
    precision = rate(caught.sum(), (predicted == "fault").sum())
    recall = rate(caught.sum(), fault.sum())
    return {
        "fault_detection_rate": rate((flagged & fault).sum(), fault.sum()),
        "fault_classification_rate": recall,
        "extreme_false_flag_rate": rate(((predicted == "fault") & extreme).sum(), extreme.sum()),
        "precision_at_k": {},
        "precision": precision,
        "recall": recall,
        "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
        "false_positive_rate_clean": rate((flagged & clean).sum(), clean.sum()),
    }


def class_scores(truth, predicted, name):
    hit = ((truth == name) & (predicted == name)).sum()
    precision = rate(hit, (predicted == name).sum())
    recall = rate(hit, (truth == name).sum())
    return {
        "total": int((truth == name).sum()),
        "predicted": int((predicted == name).sum()),
        "precision": precision,
        "recall": recall,
        "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
    }


def pick_stream(window, rng):
    picks = []
    for group, share in [("normal", 0.6), ("fault", 0.22), ("extreme", 0.18)]:
        pool = window.index[window["group"] == group]
        count = min(len(pool), int(STREAM_SIZE * share))
        if count:
            picks.extend(rng.choice(pool, count, replace=False))
    return window.loc[picks].sample(frac=1, random_state=int(rng.integers(1e6)))


def run_simulation(seed, progress=None, operating_point="balanced"):
    started = time.time()
    say = progress or (lambda *args: None)
    say("generate", 0.1, "injecting faults and extremes")
    data, first_hour = build_window(seed)

    say("features", 0.5, "building features")
    data = build_features(data)

    say("detect", 0.75, "detectors vote, booster refines")
    bank, booster = load_models()
    apply_votes(data, bank)
    proba = booster.predict_proba(data[BOOSTER_INPUTS])
    data["predicted_label"] = decide(proba, booster.classes_, operating_point)
    data["predicted_group"] = data["predicted_label"].map(label_group)
    data["score"] = 1 - proba[:, list(booster.classes_).index("normal")]
    data["baseline_flag"] = range_check(data)

    window = data[data["timestamp"] >= first_hour].reset_index(drop=True)
    truth = window["group"].to_numpy()
    predicted = window["predicted_group"].to_numpy()
    flagged = predicted != "normal"
    base_pred = np.where(window["baseline_flag"] == 1, "fault", "normal")
    unsup = window["unsupervised_group"].to_numpy()

    rng = np.random.default_rng(seed)
    stream = pick_stream(window, rng)
    records = []
    for row in stream.itertuples():
        records.append({
            "station_id": row.station_id,
            "station_name": STATIONS[row.station_id][0],
            "sensor_name": row.sensor_name,
            "unit": UNITS[row.sensor_name],
            "timestamp": str(row.timestamp),
            "measured_value": None if pd.isna(row.measured_value) else float(row.measured_value),
            "votes": [int(getattr(row, name + "_vote")) for name in DETECTORS],
            "vote_count": int(row.votes),
            "anomaly_score": round(float(row.score), 4),
            "decision": LANE[row.predicted_group],
            "reason_code": None if row.predicted_group == "normal" else row.predicted_label,
            "truth": TRUTH[row.group],
            "fault_type": row.label if row.label in FAULTS else None,
            "extreme_type": row.label if row.label in EXTREMES else None,
            "correct": row.predicted_group == row.group,
        })

    by_truth = {t: {"total": 0, "correct": 0} for t in ["clean", "fault", "extreme"]}
    by_decision = {d: {"total": 0, "correct": 0} for d in ["HEALTHY", "FAULT", "EXTREME"]}
    for record in records:
        by_truth[record["truth"]]["total"] += 1
        by_truth[record["truth"]]["correct"] += record["correct"]
        by_decision[record["decision"]]["total"] += 1
        by_decision[record["decision"]]["correct"] += record["correct"]
    correct = sum(record["correct"] for record in records)

    detector = fault_block(truth, flagged, predicted)
    baseline = fault_block(truth, base_pred != "normal", base_pred)
    per_type = {}
    base_type = {}
    for kind in FAULTS:
        rows = window["label"].to_numpy() == kind
        per_type[kind] = rate((rows & (predicted == "fault")).sum(), rows.sum())
        base_type[kind] = rate((rows & (base_pred == "fault")).sum(), rows.sum())
    lanes = {}
    for name, key in [("fault", "fault"), ("extreme", "extreme"), ("clean", "normal")]:
        total = int((truth == key).sum())
        hit = int(((truth == key) & flagged).sum())
        lanes[name] = {"total": total, "flagged": hit, "rate": rate(hit, total)}
    per_station = {}
    for code in STATIONS:
        mine = window["station_id"].to_numpy() == code
        per_station[code] = {
            "fault_detection_rate": rate((mine & flagged & (truth == "fault")).sum(), (mine & (truth == "fault")).sum()),
            "false_positive_rate_clean": rate((mine & flagged & (truth == "normal")).sum(), (mine & (truth == "normal")).sum()),
            "fault_readings": int((mine & (truth == "fault")).sum()),
            "extreme_readings": int((mine & (truth == "extreme")).sum()),
        }
    reasons = window.loc[flagged, "predicted_label"].value_counts().to_dict()
    episodes = {"fault": [], "extreme": []}
    for (code, sensor, label), part in window[window["label"] != "normal"].groupby(["station_id", "sensor_name", "label"]):
        kind = "fault" if label in FAULTS else "extreme"
        entry = {"station_id": code, "sensor_name": sensor, "start": str(part["timestamp"].min()), "end": str(part["timestamp"].max()), "affected_rows": len(part)}
        entry["fault_type" if kind == "fault" else "extreme_type"] = label
        episodes[kind].append(entry)
    extreme_episodes = len({(e["station_id"], e["extreme_type"]) for e in episodes["extreme"]})
    groups = ["normal", "fault", "extreme"]
    f1s = [class_scores(truth, predicted, g)["f1"] for g in groups]
    recalls = [class_scores(truth, predicted, g)["recall"] for g in groups]

    say("stream", 1.0, "done")
    return {
        "seed": seed,
        "window_days": WINDOW_DAYS,
        "window": {"start": str(window["timestamp"].min()), "end": str(window["timestamp"].max())},
        "counts": {
            "readings": len(window),
            "stations": len(STATIONS),
            "sensors": len(SENSORS),
            "hours": int(window["timestamp"].nunique()),
            "fault_episodes": len(episodes["fault"]),
            "extreme_episodes": extreme_episodes,
            "fault_readings": int((truth == "fault").sum()),
            "extreme_readings": int((truth == "extreme").sum()),
            "clean_readings": int((truth == "normal").sum()),
        },
        "bins": {"healthy": int((predicted == "normal").sum()), "fault": int((predicted == "fault").sum()), "extreme": int((predicted == "extreme").sum())},
        "window_accuracy": rate((truth == predicted).sum(), len(truth)),
        "balanced_accuracy": round(float(np.mean(recalls)), 4),
        "macro_f1": round(float(np.mean(f1s)), 4),
        "unsupervised_accuracy": rate((truth == unsup).sum(), len(truth)),
        "per_class": {
            "fault": class_scores(truth, predicted, "fault"),
            "extreme": class_scores(truth, predicted, "extreme"),
            "clean": class_scores(truth, predicted, "normal"),
        },
        "stream": {
            "total": len(records),
            "correct": int(correct),
            "accuracy": rate(correct, len(records)),
            "by_truth": by_truth,
            "by_decision": by_decision,
        },
        "detector": detector,
        "baseline": baseline,
        "delta": {key: round(detector[key] - baseline[key], 4) for key in ["fault_detection_rate", "extreme_false_flag_rate", "precision", "f1"]},
        "per_fault_type_recall": per_type,
        "baseline_per_fault_type_recall": base_type,
        "confusion": lanes,
        "event_metrics": {
            "event_count": len(episodes["fault"]) + len(episodes["extreme"]),
            "fault_events": len(episodes["fault"]),
            "extreme_events": extreme_episodes,
            "clean_events": 0,
            "fault_event_precision": detector["precision"],
            "extreme_event_precision": class_scores(truth, predicted, "extreme")["precision"],
            "reason_code_counts": {key: int(value) for key, value in reasons.items()},
        },
        "per_station": per_station,
        "diagnostics": {
            "vote_thresholds": {name: round(value, 3) for name, value in bank["thresholds"].items()},
            "vote_rates_reference": {name: round(float(window[name + "_vote"].mean()), 4) for name in DETECTORS},
            "pca_components": int(bank["pca"].n_components_),
            "dbscan_noise_percent": 0.0,
            "lof_outlier_percent": round(100 * float(window["lof_vote"].mean()), 2),
            "reference_rows": SAMPLE,
            "total_rows": len(window),
        },
        "timing": {"total_seconds": round(time.time() - started, 1)},
        "fault_types": [kind for kind in FAULTS if (window["label"] == kind).any()],
        "extreme_types": list(EXTREMES),
        "detectors": DETECTORS,
        "votes_needed": VOTES_NEEDED,
        "operating_point": operating_point,
        "episodes": episodes,
        "records": records,
    }
