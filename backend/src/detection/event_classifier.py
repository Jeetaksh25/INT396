import numpy as np
import pandas as pd

import config
from src.features.engineered_features import build_engineered, feature_list
from src.features.feature_builder import build_training_matrix

MIN_TRAIN_ROWS = 400


class EventClassifier:
    def __init__(self, random_state=0, max_iter=320, min_leaf=60):
        self.random_state = random_state
        self.max_iter = max_iter
        self.min_leaf = min_leaf
        self.model_ = None
        self.columns_ = None
        self.statistics_ = None
        self.fitted_ = False

    def _design(self, features, engineered):
        columns = self.columns_ or feature_list()
        frame = engineered.reindex(columns=columns)
        frame = frame.astype(float).replace([np.inf, -np.inf], np.nan)
        return frame

    def fit(self, features, labels, reference_mask):
        engineered = build_engineered(features)
        self.columns_ = feature_list()

        design = self._design(features, engineered)
        mask = np.asarray(reference_mask).astype(bool)
        reference_design = design.loc[mask].fillna(design.loc[mask].median())

        frame = features[["station_id", "timestamp", "sensor_name"]].copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        merged = frame.merge(
            labels[["station_id", "timestamp", "sensor_name", "is_fault_injected", "is_extreme_event"]],
            on=["station_id", "timestamp", "sensor_name"],
            how="left",
        )
        merged["is_fault_injected"] = merged["is_fault_injected"].fillna(0).astype(int)
        merged["is_extreme_event"] = merged["is_extreme_event"].fillna(0).astype(int)

        target = np.where(
            merged["is_fault_injected"].to_numpy() == 1,
            1,
            np.where(merged["is_extreme_event"].to_numpy() == 1, 2, 0),
        )
        mask = np.asarray(reference_mask).astype(bool)
        train_target = target[mask]

        if int((train_target > 0).sum()) < MIN_TRAIN_ROWS:
            self.fitted_ = False
            return self

        from sklearn.ensemble import HistGradientBoostingClassifier

        matrix = reference_design.to_numpy(dtype=float)
        self.statistics_ = {
            "median": reference_design.median().to_dict(),
        }

        weights = np.ones(len(train_target), dtype=float)
        for klass, weight in ((1, 3.0), (2, 3.0)):
            mask = train_target == klass
            if mask.sum():
                weights[mask] = weight

        self.model_ = HistGradientBoostingClassifier(
            max_iter=self.max_iter,
            learning_rate=0.08,
            max_leaf_nodes=31,
            min_samples_leaf=self.min_leaf,
            l2_regularization=1.0,
            random_state=self.random_state,
        ).fit(matrix, train_target, sample_weight=weights)
        self.fitted_ = True
        return self

    def predict_proba(self, features):
        if not self.fitted_ or self.model_ is None:
            return None
        engineered = build_engineered(features)
        design = self._design(features, engineered)
        design = design.fillna(pd.Series(self.statistics_["median"]))
        matrix = design.to_numpy(dtype=float)
        probability = self.model_.predict_proba(matrix)
        classes = list(self.model_.classes_)
        output = np.zeros((len(matrix), 3), dtype=float)
        for position, klass in enumerate(classes):
            output[:, int(klass)] = probability[:, position]
        return output


def event_decisions(features, probabilities, anomaly_mask, threshold=0.5):
    if probabilities is None:
        return np.where(anomaly_mask, "FAULT", "HEALTHY"), np.zeros(len(features))

    fault_probability = probabilities[:, 1]
    extreme_probability = probabilities[:, 2]
    decisions = np.full(len(features), "HEALTHY", dtype=object)
    flagged = anomaly_mask.astype(bool)
    decisions[flagged] = "FAULT"
    extreme_choice = flagged & (extreme_probability > fault_probability) & (
        extreme_probability > threshold
    )
    decisions[extreme_choice] = "EXTREME"
    confidence = np.maximum(fault_probability, extreme_probability)
    return decisions, confidence
