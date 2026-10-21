import pandas as pd

from src.features.leakage_guard import assert_no_labels, strip_label_columns


def test_guard_rejects_labels():
    labelled = pd.DataFrame(
        {
            "station_id": ["DEL"],
            "is_fault_injected": [1],
            "fault_type": ["bias"],
        }
    )
    try:
        assert_no_labels(labelled, "unit test")
    except ValueError:
        print("guard rejects labelled frame ok")
        return
    raise AssertionError("guard failed to reject labels")


def test_guard_accepts_clean_frame():
    clean = pd.DataFrame({"station_id": ["DEL"], "measured_value": [24.0]})
    assert assert_no_labels(clean, "unit test")
    print("guard accepts clean frame ok")


def test_strip_removes_labels():
    labelled = pd.DataFrame(
        {
            "station_id": ["DEL"],
            "measured_value": [24.0],
            "is_fault_injected": [1],
            "is_extreme_event": [0],
            "fault_type": ["bias"],
            "extreme_type": [""],
        }
    )
    stripped = strip_label_columns(labelled)
    assert "is_fault_injected" not in stripped.columns
    assert "is_extreme_event" not in stripped.columns
    assert "measured_value" in stripped.columns
    assert assert_no_labels(stripped, "unit test")
    print("strip removes label columns ok")


if __name__ == "__main__":
    test_guard_rejects_labels()
    test_guard_accepts_clean_frame()
    test_strip_removes_labels()
    print("all leakage tests passed")
