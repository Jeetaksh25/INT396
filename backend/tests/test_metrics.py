import numpy as np
import pandas as pd

from src.evaluation.metrics import (
    extreme_false_flag_rate,
    fault_detection_rate,
    precision_at_k,
    precision_recall_f1,
)


def build_labels():
    return pd.DataFrame(
        {
            "is_fault_injected": [1, 1, 0, 0, 0],
            "is_extreme_event": [0, 0, 1, 1, 0],
            "fault_type": ["bias", "stuck", "", "", ""],
        }
    )


def test_fault_detection_rate():
    labels = build_labels()
    flags = np.array([1, 0, 1, 0, 0])
    assert abs(fault_detection_rate(flags, labels) - 0.5) < 1e-9
    print("fault detection rate ok")


def test_extreme_false_flag_rate():
    labels = build_labels()
    event_labels = np.array(["FAULT", "FAULT", "FAULT", "EXTREME", ""])
    assert abs(extreme_false_flag_rate(event_labels, labels) - 0.5) < 1e-9
    print("extreme false flag rate ok")


def test_precision_at_k():
    labels = build_labels()
    scores = np.array([0.9, 0.2, 0.85, 0.1, 0.0])
    assert abs(precision_at_k(scores, labels, 2) - 1.0) < 1e-9
    assert abs(precision_at_k(scores, labels, 5) - 0.8) < 1e-9
    print("precision at k ok")


def test_precision_recall_f1():
    labels = build_labels()
    flags = np.array([1, 1, 0, 1, 0])
    precision, recall, f1 = precision_recall_f1(flags, labels)
    assert abs(precision - 0.6666666) < 1e-5
    assert abs(recall - 1.0) < 1e-9
    assert abs(f1 - 0.8) < 1e-9
    print("precision recall f1 ok")


if __name__ == "__main__":
    test_fault_detection_rate()
    test_extreme_false_flag_rate()
    test_precision_at_k()
    test_precision_recall_f1()
    print("all metric tests passed")
