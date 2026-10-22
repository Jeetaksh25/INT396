import pickle
import threading
import time

import numpy as np
import pandas as pd

import config
from src.detection.baseline_range_check import build_baseline_table
from src.detection.consensus_detector import (
    assemble_detections,
    fit_consensus,
    score_with_bank,
)
from src.detection.extreme_discriminator import apply_event_labels, classify_all_events
from src.evaluation.metrics import build_event_metrics, evaluate_all
from src.features.feature_builder import build_all_features, build_training_matrix, reference_mask_for
from src.features.rule_features import mine_weather_rules, rule_violations_for_wide
from src.simulation.extreme_events import apply_extreme_episodes
from src.simulation.fault_models import apply_fault_episodes

DETECTOR_NAMES = ["kmeans", "dbscan", "pca", "isolation", "lof"]

STREAM_TARGET = 96

WINDOW_DAYS = 21

FAULTS_PER_TYPE = 2

EXTREMES_PER_TYPE = 1

TRAIN_FRACTION = 0.35

TRAINED_BANK_PATH = config.RESULTS_DIR / "simulation_bank.pkl"

BANK_VERSION = 3

_lock = threading.Lock()

_trained = {}


def load_clean_frame():
    clean = pd.read_parquet(config.PROCESSED_DIR / "clean_wide.parquet")
    clean["timestamp"] = pd.to_datetime(clean["timestamp"])
    return clean.set_index(["station_id", "timestamp"]).sort_index()


def train_bank(clean_wide, progress=None, operating_point=None):
    if progress is not None:
        progress("train", 0.05, "mining association rules")
    rules = mine_weather_rules(clean_wide.reset_index())
    violations = rule_violations_for_wide(clean_wide[list(config.SENSORS)], rules)

    if progress is not None:
        progress("train", 0.2, "building feature matrix")
    features, _ = build_all_features(clean_wide[list(config.SENSORS)], rule_violations=violations)
    reference_mask = reference_mask_for(features, TRAIN_FRACTION)
    _, matrix, statistics = build_training_matrix(features, reference_mask)

    if progress is not None:
        progress("train", 0.45, "fitting five detectors")
    bank = fit_consensus(matrix[reference_mask], operating_point=operating_point)
    bank["statistics"] = statistics
    bank["rules"] = rules
    bank["reference_rows"] = int(reference_mask.sum())
    bank["version"] = BANK_VERSION
    return bank


def get_trained(progress=None, operating_point=None):
    with _lock:
        cache_key = operating_point or config.DEFAULT_OPERATING_POINT
        if _trained.get("key") == cache_key and "bank" in _trained:
            return _trained["bank"]

        clean_wide = load_clean_frame()
        _trained["clean_wide"] = clean_wide

        if TRAINED_BANK_PATH.exists():
            if progress is not None:
                progress("train", 0.3, "loading cached detector bank")
            try:
                with TRAINED_BANK_PATH.open("rb") as handle:
                    bank = pickle.load(handle)
                if (
                    bank.get("version") == BANK_VERSION
                    and "ensemble_threshold" in bank
                    and bank.get("operating_point") == cache_key
                ):
                    _trained["key"] = cache_key
                    _trained["bank"] = bank
                    return bank
            except Exception:
                pass

        bank = train_bank(clean_wide, progress=progress, operating_point=operating_point)
        _trained["key"] = cache_key
        _trained["bank"] = bank
        try:
            TRAINED_BANK_PATH.parent.mkdir(parents=True, exist_ok=True)
            with TRAINED_BANK_PATH.open("wb") as handle:
                pickle.dump(bank, handle, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass
        return bank


def scale_matrix(features, statistics):
    columns = []
    for column in config.FEATURE_COLUMNS:
        values = features[column].astype(float).to_numpy()
        mean_value = statistics[column]["mean"]
        std_value = statistics[column]["std"]
        columns.append((values - mean_value) / std_value)
    matrix = np.column_stack(columns)
    return np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)


def slice_window(wide_frame, seed):
    timestamps = wide_frame.index.get_level_values("timestamp")
    unique_hours = np.sort(pd.unique(timestamps))
    span = min(WINDOW_DAYS * 24, len(unique_hours))
    latest_start = max(0, len(unique_hours) - span)
    start_index = 0 if latest_start == 0 else int((seed * 4099) % latest_start)
    return unique_hours[start_index:start_index + span]


def blank_wide(frame):
    frame = frame.copy()
    frame["is_extreme_event"] = 0
    frame["extreme_type"] = ""
    return frame


def long_form(wide, values):
    blocks = []
    for station_id in sorted(wide.index.get_level_values("station_id").unique()):
        station_series = values.xs(station_id, level="station_id")
        block = station_series.stack().reset_index()
        block.columns = ["timestamp", "sensor_name", "measured_value"]
        block["station_id"] = station_id
        blocks.append(block)
    frame = pd.concat(blocks, ignore_index=True)
    return frame[
        ["station_id", "timestamp", "sensor_name", "measured_value"]
    ].sort_values(["station_id", "sensor_name", "timestamp"]).reset_index(drop=True)


def inject_events(window, seed):
    wide = blank_wide(window)

    wide, extreme_episodes = apply_extreme_episodes(
        wide,
        np.random.default_rng(seed + 11),
        episodes_per_type=EXTREMES_PER_TYPE,
    )

    long_frame = long_form(wide, wide[list(config.SENSORS)])
    long_frame["clean_value"] = long_frame["measured_value"]
    long_frame["is_extreme_event"] = (
        wide["is_extreme_event"]
        .reindex(pd.MultiIndex.from_frame(long_frame[["station_id", "timestamp"]]))
        .to_numpy()
    )
    long_frame["extreme_type"] = (
        wide["extreme_type"]
        .reindex(pd.MultiIndex.from_frame(long_frame[["station_id", "timestamp"]]))
        .to_numpy()
    )
    long_frame["is_extreme_event"] = long_frame["is_extreme_event"].fillna(0).astype(int)
    long_frame["extreme_type"] = long_frame["extreme_type"].fillna("")

    long_frame, fault_episodes = apply_fault_episodes(
        long_frame,
        np.random.default_rng(seed + 29),
        episodes_per_type=FAULTS_PER_TYPE,
    )

    measured = long_frame.pivot_table(
        index=["station_id", "timestamp"],
        columns="sensor_name",
        values="measured_value",
        aggfunc="first",
    ).reindex(columns=list(config.SENSORS)).sort_index()

    return long_frame, measured, wide, fault_episodes, extreme_episodes


def run_detection(features, measured, bank):
    matrix = scale_matrix(features, bank["statistics"])
    scores, labels, components = score_with_bank(bank["bank"], matrix)
    detections = assemble_detections(
        features,
        scores,
        labels,
        bank["thresholds"],
        ensemble_threshold=bank.get("ensemble_threshold"),
        deviation_gate=bank.get("deviation_gate"),
    )
    detections["pca_components"] = components

    baseline = build_baseline_table(features)
    detections = detections.merge(
        baseline[["station_id", "sensor_name", "timestamp", "baseline_flag"]],
        on=["station_id", "timestamp", "sensor_name"],
        how="left",
    )

    standardized = features.copy()
    for column in config.FEATURE_COLUMNS:
        values = standardized[column].astype(float)
        standardized[column] = (
            values - bank["statistics"][column]["mean"]
        ) / bank["statistics"][column]["std"]
    events = classify_all_events(detections, standardized)
    labelled = apply_event_labels(detections, events)

    diagnostics = {
        "operating_point": bank.get("operating_point"),
        "deviation_gate": bank.get("deviation_gate"),
        "ensemble_threshold": bank.get("ensemble_threshold"),
        "vote_thresholds": dict(bank["thresholds"]),
        "vote_rates_reference": dict(bank["vote_rates"]),
        "pca_components": int(components),
        "dbscan_noise_percent": float(100.0 * np.mean(labels["dbscan"] == -1)),
        "lof_outlier_percent": float(
            100.0 * np.mean(scores["lof_score"] > bank["thresholds"]["lof_vote"])
        ),
        "reference_rows": int(bank["reference_rows"]),
        "total_rows": int(len(matrix)),
    }
    return labelled, events, diagnostics


def truth_for(row):
    if int(row["is_fault_injected"]) == 1:
        return "fault"
    if int(row["is_extreme_event"]) == 1:
        return "extreme"
    return "clean"


def expected_decision(truth):
    if truth == "fault":
        return "FAULT"
    if truth == "extreme":
        return "EXTREME"
    return "HEALTHY"


def pick_stream(detections, labels, target=STREAM_TARGET):
    merged = detections.merge(
        labels[
            [
                "station_id",
                "timestamp",
                "sensor_name",
                "is_fault_injected",
                "is_extreme_event",
                "fault_type",
                "extreme_type",
            ]
        ],
        on=["station_id", "timestamp", "sensor_name"],
        how="left",
    )
    merged["is_fault_injected"] = merged["is_fault_injected"].fillna(0).astype(int)
    merged["is_extreme_event"] = merged["is_extreme_event"].fillna(0).astype(int)
    merged["fault_type"] = merged["fault_type"].fillna("")
    merged["extreme_type"] = merged["extreme_type"].fillna("")
    merged["truth"] = [truth_for(row) for _, row in merged.iterrows()]

    merged["decision"] = "HEALTHY"
    merged.loc[merged["event_label"] == "FAULT", "decision"] = "FAULT"
    merged.loc[merged["event_label"] == "EXTREME", "decision"] = "EXTREME"
    merged["correct"] = [
        decision == expected_decision(truth)
        for decision, truth in zip(merged["decision"], merged["truth"])
    ]
    merged = merged.sort_values(["timestamp", "station_id", "sensor_name"]).reset_index(drop=True)

    flagged = merged.index[merged["is_local_anomaly"] == 1].to_numpy()
    quiet = merged.index[merged["is_local_anomaly"] == 0].to_numpy()

    detected_budget = int(round(target * 0.42))
    chosen = []
    if len(flagged):
        limit = min(len(flagged), detected_budget)
        chosen.extend(
            int(item)
            for item in flagged[np.linspace(0, len(flagged) - 1, limit).astype(int)]
        )

    remaining = target - len(chosen)
    if len(quiet) and remaining > 0:
        limit = min(len(quiet), remaining)
        chosen.extend(
            int(item) for item in quiet[np.linspace(0, len(quiet) - 1, limit).astype(int)]
        )

    shortfall = target - len(chosen)
    if shortfall > 0:
        spare = merged.index[~merged.index.isin(chosen)].to_numpy()
        if len(spare):
            needed = min(shortfall, len(spare))
            chosen.extend(
                int(item) for item in spare[np.linspace(0, len(spare) - 1, needed).astype(int)]
            )

    subset = merged.loc[sorted(chosen)]

    records = []
    for _, row in subset.iterrows():
        records.append(
            {
                "station_id": str(row["station_id"]),
                "station_name": config.STATION_REGISTRY[str(row["station_id"])]["name"],
                "sensor_name": str(row["sensor_name"]),
                "unit": config.SENSOR_UNITS[str(row["sensor_name"])],
                "timestamp": str(pd.Timestamp(row["timestamp"])),
                "measured_value": None
                if pd.isna(row["measured_value"])
                else round(float(row["measured_value"]), 1),
                "votes": [int(row[f"{name}_vote"]) for name in DETECTOR_NAMES],
                "vote_count": int(row["vote_count"]),
                "anomaly_score": round(float(row["anomaly_score"]), 2),
                "decision": str(row["decision"]),
                "reason_code": None if pd.isna(row["reason_code"]) else str(row["reason_code"]),
                "truth": row["truth"],
                "fault_type": str(row["fault_type"]) if row["fault_type"] else None,
                "extreme_type": str(row["extreme_type"]) if row["extreme_type"] else None,
                "correct": bool(row["correct"]),
            }
        )
    return records


def build_summary(detections, labels, records, episodes, seed, window, diagnostics, timing):
    metrics, merged = evaluate_all(detections, labels)
    confusion = metrics["confusion"]

    def rate(total, flagged):
        return {
            "total": int(total),
            "flagged": int(flagged),
            "rate": round(float(flagged) / float(total), 4) if total else 0.0,
        }

    correct = sum(1 for record in records if record["correct"])

    merged["truth_label"] = np.where(
        merged["is_fault_injected"] == 1,
        "fault",
        np.where(merged["is_extreme_event"] == 1, "extreme", "clean"),
    )
    merged["decision_label"] = "HEALTHY"
    merged.loc[merged["event_label"] == "FAULT", "decision_label"] = "FAULT"
    merged.loc[merged["event_label"] == "EXTREME", "decision_label"] = "EXTREME"
    merged["decision_matches"] = merged["decision_label"] == np.where(
        merged["truth_label"] == "fault",
        "FAULT",
        np.where(merged["truth_label"] == "extreme", "EXTREME", "HEALTHY"),
    )

    per_class = {}
    for truth_key, decision_key in (
        ("fault", "FAULT"),
        ("extreme", "EXTREME"),
        ("clean", "HEALTHY"),
    ):
        truth_mask = merged["truth_label"] == truth_key
        total = int(truth_mask.sum())
        hit = int((truth_mask & merged["decision_matches"]).sum())
        predicted = int((merged["decision_label"] == decision_key).sum())
        true_positive = hit
        precision = true_positive / predicted if predicted else 0.0
        recall = hit / total if total else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        per_class[truth_key] = {
            "total": total,
            "predicted": predicted,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    recalls = [block["recall"] for block in per_class.values() if block["total"]]
    balanced = float(np.mean(recalls)) if recalls else 0.0
    macro_f1 = float(np.mean([block["f1"] for block in per_class.values()]))
    window_accuracy = float(merged["decision_matches"].mean())

    return {
        "seed": seed,
        "window_days": WINDOW_DAYS,
        "window_accuracy": round(window_accuracy, 4),
        "balanced_accuracy": round(balanced, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "window": window,
        "counts": {
            "readings": int(len(detections)),
            "stations": int(detections["station_id"].nunique()),
            "sensors": int(detections["sensor_name"].nunique()),
            "hours": int(pd.to_datetime(detections["timestamp"]).nunique()),
            "fault_episodes": int(len(episodes["fault"])),
            "extreme_episodes": int(len(episodes["extreme"])),
            "fault_readings": int((merged["is_fault_injected"] == 1).sum()),
            "extreme_readings": int((merged["is_extreme_event"] == 1).sum()),
            "clean_readings": int(confusion["clean_total"]),
        },
        "bins": {
            "healthy": int((detections["is_local_anomaly"] == 0).sum()),
            "fault": int((detections["event_label"] == "FAULT").sum()),
            "extreme": int((detections["event_label"] == "EXTREME").sum()),
        },
        "stream": {
            "total": len(records),
            "correct": int(correct),
            "accuracy": round(correct / len(records), 4) if records else 0.0,
            "by_truth": {
                key: {
                    "total": sum(1 for r in records if r["truth"] == key),
                    "correct": sum(1 for r in records if r["truth"] == key and r["correct"]),
                }
                for key in ("fault", "extreme", "clean")
            },
            "by_decision": {
                key: {
                    "total": sum(1 for r in records if r["decision"] == key),
                    "correct": sum(
                        1 for r in records if r["decision"] == key and r["correct"]
                    ),
                }
                for key in ("FAULT", "EXTREME", "HEALTHY")
            },
        },
        "detector": metrics["detector"],
        "baseline": metrics["baseline_range_check"],
        "delta": metrics["delta"],
        "per_fault_type_recall": metrics["per_fault_type_recall"],
        "baseline_per_fault_type_recall": metrics["baseline_per_fault_type_recall"],
        "confusion": {
            "fault": rate(confusion["fault_total"], confusion["fault_flagged"]),
            "extreme": rate(confusion["extreme_total"], confusion["extreme_flagged"]),
            "clean": rate(confusion["clean_total"], confusion["clean_flagged"]),
        },
        "event_metrics": build_event_metrics(episodes["events"], merged),
        "per_station": metrics["per_station"],
        "diagnostics": diagnostics,
        "timing": timing,
        "fault_types": config.FAULT_TYPES,
        "extreme_types": config.EXTREME_TYPES,
        "detectors": DETECTOR_NAMES,
        "operating_point": diagnostics.get("operating_point", config.DEFAULT_OPERATING_POINT),
        "episodes": {
            "fault": episodes["fault"],
            "extreme": episodes["extreme"],
        },
        "records": records,
    }


def run_simulation(seed, progress=None, operating_point=None):
    started = time.time()

    def report(phase, fraction, detail=""):
        if progress is not None:
            progress(phase, fraction, detail)

    report("train", 0.02, "preparing model bank")
    bank = get_trained(progress=report, operating_point=operating_point)
    clean_wide = _trained["clean_wide"]

    report("generate", 0.55, "cutting random window")
    hours = slice_window(clean_wide, seed)
    window = clean_wide.loc[
        np.isin(clean_wide.index.get_level_values("timestamp"), hours)
    ].copy()

    report("generate", 0.62, "injecting weather extremes")
    labelled_long, measured, wide_measured, fault_episodes, extreme_episodes = inject_events(
        window, seed
    )

    report("features", 0.7, "building feature columns")
    violations = rule_violations_for_wide(measured[list(config.SENSORS)], bank["rules"])
    features, _ = build_all_features(
        measured[list(config.SENSORS)], rule_violations=violations
    )

    report("detect", 0.82, "consensus voting")
    detections, events, diagnostics = run_detection(features, measured, bank)

    dataset_labels = labelled_long[
        [
            "station_id",
            "timestamp",
            "sensor_name",
            "is_fault_injected",
            "is_extreme_event",
            "fault_type",
            "extreme_type",
        ]
    ].copy()

    report("stream", 0.93, "sampling readings")
    records = pick_stream(detections, dataset_labels)

    report("report", 0.98, "scoring")
    timing = {
        "total_seconds": round(time.time() - started, 2),
        "feature_seconds": 0.0,
        "score_seconds": 0.0,
    }
    summary = build_summary(
        detections,
        dataset_labels,
        records,
        {"fault": fault_episodes, "extreme": extreme_episodes, "events": events},
        seed,
        {"start": str(pd.Timestamp(hours[0])), "end": str(pd.Timestamp(hours[-1]))},
        diagnostics,
        timing,
    )
    summary["timing"]["total_seconds"] = round(time.time() - started, 2)
    report("report", 1.0, "done")
    return summary
