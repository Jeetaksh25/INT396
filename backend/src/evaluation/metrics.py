import numpy as np
import pandas as pd

import config


def safe_divide(numerator, denominator):
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def fault_detection_rate(detection_flags, labels):
    fault_mask = labels["is_fault_injected"].to_numpy() == 1
    if fault_mask.sum() == 0:
        return 0.0
    return safe_divide(np.sum(detection_flags[fault_mask]), fault_mask.sum())


def fault_classification_rate(event_labels, labels):
    fault_mask = labels["is_fault_injected"].to_numpy() == 1
    if fault_mask.sum() == 0:
        return 0.0
    classified = (event_labels == "FAULT") & fault_mask
    return safe_divide(np.sum(classified), fault_mask.sum())


def extreme_false_flag_rate(event_labels, labels):
    extreme_mask = labels["is_extreme_event"].to_numpy() == 1
    if extreme_mask.sum() == 0:
        return 0.0
    flagged_as_fault = (event_labels == "FAULT") & extreme_mask
    return safe_divide(np.sum(flagged_as_fault), extreme_mask.sum())


def precision_at_k(anomaly_scores, labels, k):
    ranked = np.argsort(-anomaly_scores)
    top_k = ranked[: min(k, len(ranked))]
    is_true_anomaly = (
        (labels["is_fault_injected"].to_numpy() == 1)
        | (labels["is_extreme_event"].to_numpy() == 1)
    )
    return safe_divide(np.sum(is_true_anomaly[top_k]), len(top_k))


def precision_recall_f1(detection_flags, labels):
    truth = (labels["is_fault_injected"].to_numpy() == 1).astype(int)
    predicted = np.asarray(detection_flags).astype(int)
    true_positive = int(np.sum((predicted == 1) & (truth == 1)))
    false_positive = int(np.sum((predicted == 1) & (truth == 0)))
    false_negative = int(np.sum((predicted == 0) & (truth == 1)))
    precision = safe_divide(true_positive, true_positive + false_positive)
    recall = safe_divide(true_positive, true_positive + false_negative)
    f1 = safe_divide(2 * precision * recall, precision + recall)
    return precision, recall, f1


def false_positive_rate_clean(detection_flags, labels):
    clean_mask = (
        (labels["is_fault_injected"].to_numpy() == 0)
        & (labels["is_extreme_event"].to_numpy() == 0)
    )
    if clean_mask.sum() == 0:
        return 0.0
    return safe_divide(np.sum(np.asarray(detection_flags)[clean_mask]), clean_mask.sum())


def per_fault_type_recall(detection_flags, labels):
    fault_types = labels["fault_type"].fillna("").to_numpy()
    flags = np.asarray(detection_flags)
    result = {}
    for fault_name in config.FAULT_TYPES:
        mask = fault_types == fault_name
        result[fault_name] = safe_divide(np.sum(flags[mask]), int(mask.sum()))
    return result


def per_station_metrics(detection_flags, labels):
    result = {}
    station_ids = labels["station_id"].to_numpy()
    for station_id in config.STATION_REGISTRY:
        mask = station_ids == station_id
        station_labels = labels[mask]
        station_flags = np.asarray(detection_flags)[mask]
        result[station_id] = {
            "fault_detection_rate": fault_detection_rate(station_flags, station_labels),
            "false_positive_rate_clean": false_positive_rate_clean(station_flags, station_labels),
            "fault_readings": int(station_labels["is_fault_injected"].sum()),
            "extreme_readings": int(station_labels["is_extreme_event"].sum()),
        }
    return result


def build_metric_block(detection_flags, anomaly_scores, event_labels, labels):
    precision, recall, f1 = precision_recall_f1(detection_flags, labels)
    return {
        "fault_detection_rate": round(fault_detection_rate(detection_flags, labels), 4),
        "fault_classification_rate": round(fault_classification_rate(event_labels, labels), 4),
        "extreme_false_flag_rate": round(extreme_false_flag_rate(event_labels, labels), 4),
        "precision_at_k": {
            str(k): round(precision_at_k(anomaly_scores, labels, k), 4)
            for k in config.PRECISION_AT_K_VALUES
        },
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate_clean": round(false_positive_rate_clean(detection_flags, labels), 4),
    }


def evaluate_all(detections, labels):
    merged = detections.merge(
        labels, on=["station_id", "timestamp", "sensor_name"], how="left"
    )
    merged["is_fault_injected"] = merged["is_fault_injected"].fillna(0).astype(int)
    merged["is_extreme_event"] = merged["is_extreme_event"].fillna(0).astype(int)
    merged["fault_type"] = merged["fault_type"].fillna("")
    merged["extreme_type"] = merged["extreme_type"].fillna("")

    anomaly_flags = merged["is_anomaly"].to_numpy()
    anomaly_scores = merged["anomaly_score"].to_numpy(dtype=float)
    event_labels = merged["event_label"].fillna("").to_numpy()
    baseline_flags = merged["baseline_flag"].to_numpy()

    baseline_event_labels = np.where(baseline_flags == 1, "FAULT", "")
    detector_block = build_metric_block(anomaly_flags, anomaly_scores, event_labels, merged)
    baseline_block = build_metric_block(
        baseline_flags,
        baseline_flags.astype(float),
        baseline_event_labels,
        merged,
    )

    result = {
        "detector": detector_block,
        "baseline_range_check": baseline_block,
        "delta": {
            "fault_detection_rate": round(
                detector_block["fault_detection_rate"] - baseline_block["fault_detection_rate"], 4
            ),
            "extreme_false_flag_rate": round(
                baseline_block["extreme_false_flag_rate"] - detector_block["extreme_false_flag_rate"], 4
            ),
            "precision": round(detector_block["precision"] - baseline_block["precision"], 4),
            "f1": round(detector_block["f1"] - baseline_block["f1"], 4),
        },
        "per_fault_type_recall": {
            name: round(value, 4)
            for name, value in per_fault_type_recall(anomaly_flags, merged).items()
        },
        "baseline_per_fault_type_recall": {
            name: round(value, 4)
            for name, value in per_fault_type_recall(baseline_flags, merged).items()
        },
        "per_station": per_station_metrics(anomaly_flags, merged),
        "label_counts": {
            "total_readings": int(len(merged)),
            "fault_readings": int(merged["is_fault_injected"].sum()),
            "extreme_readings": int(merged["is_extreme_event"].sum()),
        },
        "confusion": build_confusion(anomaly_flags, merged),
    }
    return result, merged


def build_confusion(anomaly_flags, merged):
    fault_mask = merged["is_fault_injected"].to_numpy() == 1
    extreme_mask = merged["is_extreme_event"].to_numpy() == 1
    clean_mask = ~(fault_mask | extreme_mask)
    flags = np.asarray(anomaly_flags)
    return {
        "fault_flagged": int(np.sum(flags[fault_mask])),
        "fault_total": int(fault_mask.sum()),
        "extreme_flagged": int(np.sum(flags[extreme_mask])),
        "extreme_total": int(extreme_mask.sum()),
        "clean_flagged": int(np.sum(flags[clean_mask])),
        "clean_total": int(clean_mask.sum()),
    }


def build_event_metrics(events_frame, labelled_detections):
    if len(events_frame) == 0:
        return {"event_count": 0}
    truth = labelled_detections.groupby(["station_id", "sensor_name", "timestamp"]).agg(
        is_fault=("is_fault_injected", "max"),
        is_extreme=("is_extreme_event", "max"),
    )
    event_rows = []
    for row in events_frame.itertuples():
        mask = (
            (truth.index.get_level_values("station_id") == row.station_id)
            & (truth.index.get_level_values("sensor_name") == row.sensor_name)
            & (truth.index.get_level_values("timestamp") >= row.start)
            & (truth.index.get_level_values("timestamp") <= row.end)
        )
        window = truth[mask]
        actual_faults = int(window["is_fault"].sum())
        actual_extremes = int(window["is_extreme"].sum())
        if actual_faults == 0 and actual_extremes == 0:
            true_label = "clean"
        elif actual_faults >= actual_extremes:
            true_label = "FAULT"
        else:
            true_label = "EXTREME"
        event_rows.append(
            {
                "event_id": row.event_id,
                "label": row.label,
                "true_label": true_label,
                "reason_code": row.reason_code,
            }
        )
    event_truth = pd.DataFrame(event_rows)
    fault_events = event_truth[event_truth["true_label"] == "FAULT"]
    extreme_events = event_truth[event_truth["true_label"] == "EXTREME"]
    clean_events = event_truth[event_truth["true_label"] == "clean"]
    return {
        "event_count": int(len(event_truth)),
        "fault_events": int(len(fault_events)),
        "extreme_events": int(len(extreme_events)),
        "clean_events": int(len(clean_events)),
        "fault_event_precision": round(
            safe_divide((fault_events["label"] == "FAULT").sum(), len(fault_events)), 4
        ),
        "extreme_event_precision": round(
            safe_divide((extreme_events["label"] == "EXTREME").sum(), len(extreme_events)), 4
        ),
        "reason_code_counts": event_truth["reason_code"].value_counts().to_dict(),
    }
