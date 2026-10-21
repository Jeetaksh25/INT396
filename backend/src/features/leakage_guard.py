import pandas as pd

TRAINING_COLUMNS = [
    "station_id",
    "timestamp",
    "sensor_name",
    "measured_value",
    "clean_value",
    "precipitation",
]

LABEL_COLUMNS = [
    "is_fault_injected",
    "fault_type",
    "is_extreme_event",
    "extreme_type",
]


def assert_no_labels(frame, stage_name):
    present = [column for column in LABEL_COLUMNS if column in frame.columns]
    if present:
        raise ValueError(f"label columns reached the model path at {stage_name}: {present}")
    return True


def assert_unsupervised_inputs(dataset, clean_wide, detection_inputs):
    if "measured_value" not in dataset.columns:
        raise ValueError("dataset must expose measured_value")
    assert_no_labels(clean_wide, "clean reference frame")
    for name, frame in detection_inputs.items():
        assert_no_labels(frame, name)
    return True


def strip_label_columns(frame):
    return frame.drop(columns=[column for column in LABEL_COLUMNS if column in frame.columns])


def build_label_free_dataset(dataset):
    assert_no_labels(dataset, "raw dataset")
    return dataset.copy()
