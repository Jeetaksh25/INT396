import numpy as np


class StandardScalerCustom:
    def __init__(self):
        self.mean_ = None
        self.scale_ = None

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        self.mean_ = np.mean(feature_matrix, axis=0)
        self.scale_ = np.std(feature_matrix, axis=0)
        self.scale_[self.scale_ == 0.0] = 1.0
        return self

    def transform(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        return (feature_matrix - self.mean_) / self.scale_

    def fit_transform(self, feature_matrix):
        self.fit(feature_matrix)
        return self.transform(feature_matrix)


class MinMaxScalerCustom:
    def __init__(self):
        self.min_ = None
        self.range_ = None

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        self.min_ = np.min(feature_matrix, axis=0)
        maximum = np.max(feature_matrix, axis=0)
        self.range_ = maximum - self.min_
        self.range_[self.range_ == 0.0] = 1.0
        return self

    def transform(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        return (feature_matrix - self.min_) / self.range_

    def fit_transform(self, feature_matrix):
        self.fit(feature_matrix)
        return self.transform(feature_matrix)
