import numpy as np


class PCACustom:
    def __init__(self, n_components=None):
        self.n_components = n_components
        self.mean_ = None
        self.components_ = None
        self.eigenvalues_ = None
        self.explained_variance_ratio_ = None

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        n_rows = feature_matrix.shape[0]
        self.mean_ = np.mean(feature_matrix, axis=0)
        centered = feature_matrix - self.mean_

        covariance = centered.T @ centered / max(n_rows - 1, 1)
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)

        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[order]
        eigenvectors = eigenvectors[:, order]

        for column in range(eigenvectors.shape[1]):
            largest_row = int(np.argmax(np.abs(eigenvectors[:, column])))
            if eigenvectors[largest_row, column] < 0.0:
                eigenvectors[:, column] = -eigenvectors[:, column]

        self.eigenvalues_ = np.maximum(eigenvalues, 0.0)
        self.components_ = eigenvectors

        total_variance = float(np.sum(self.eigenvalues_))
        if total_variance > 0.0:
            self.explained_variance_ratio_ = self.eigenvalues_ / total_variance
        else:
            self.explained_variance_ratio_ = np.zeros_like(self.eigenvalues_)
        return self

    def _component_count(self, n_components):
        if n_components is not None:
            return int(n_components)
        if self.n_components is not None:
            return int(self.n_components)
        return self.components_.shape[1]

    def transform(self, feature_matrix, n_components=None):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        count = self._component_count(n_components)
        components = self.components_[:, :count]
        return (feature_matrix - self.mean_) @ components

    def inverse_transform(self, reduced_matrix, n_components=None):
        reduced_matrix = np.asarray(reduced_matrix, dtype=float)
        count = self._component_count(n_components)
        components = self.components_[:, :count]
        return reduced_matrix @ components.T + self.mean_

    def reconstruction_error(self, feature_matrix, n_components=None):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        reduced = self.transform(feature_matrix, n_components)
        reconstructed = self.inverse_transform(reduced, n_components)
        difference = feature_matrix - reconstructed
        return np.sum(difference * difference, axis=1)
