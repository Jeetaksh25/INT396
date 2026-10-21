import numpy as np

from src.algorithms.distance_metrics import pairwise_distances


class DBSCANCustom:
    def __init__(self, eps=1.0, min_samples=5, distance="euclidean", max_fit_samples=6000):
        self.eps = eps
        self.min_samples = min_samples
        self.distance = distance
        self.max_fit_samples = max_fit_samples
        self.core_samples_ = None
        self.core_labels_ = None

    def _region_labels(self, feature_matrix):
        n_rows = feature_matrix.shape[0]
        neighbours = []
        chunk_size = 1024
        for start in range(0, n_rows, chunk_size):
            end = min(start + chunk_size, n_rows)
            chunk_distances = pairwise_distances(
                feature_matrix[start:end], feature_matrix, self.distance
            )
            neighbours.append(chunk_distances <= self.eps)
        neighbours = np.vstack(neighbours)
        neighbour_counts = np.sum(neighbours, axis=1)

        labels = np.full(n_rows, -1, dtype=int)
        visited = np.zeros(n_rows, dtype=bool)
        cluster_id = 0

        for start in range(n_rows):
            if visited[start]:
                continue
            visited[start] = True
            if neighbour_counts[start] < self.min_samples:
                continue

            labels[start] = cluster_id
            queue = [start]
            position = 0
            while position < len(queue):
                current = queue[position]
                position += 1
                if neighbour_counts[current] >= self.min_samples:
                    for candidate in np.flatnonzero(neighbours[current]):
                        candidate = int(candidate)
                        if not visited[candidate]:
                            visited[candidate] = True
                            labels[candidate] = cluster_id
                            queue.append(candidate)
                        elif labels[candidate] == -1:
                            labels[candidate] = cluster_id
            cluster_id += 1
        return labels

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        n_rows = feature_matrix.shape[0]
        if n_rows > self.max_fit_samples:
            step = max(1, n_rows // self.max_fit_samples)
            indices = np.arange(0, n_rows, step)[: self.max_fit_samples]
            fit_matrix = feature_matrix[indices]
        else:
            fit_matrix = feature_matrix

        fit_labels = self._region_labels(fit_matrix)
        core_mask = fit_labels >= 0
        self.core_samples_ = fit_matrix[core_mask]
        self.core_labels_ = fit_labels[core_mask]
        self.labels_ = fit_labels
        return fit_labels

    def predict(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        if self.core_samples_ is None or len(self.core_samples_) == 0:
            return np.full(feature_matrix.shape[0], -1, dtype=int)

        labels = np.full(feature_matrix.shape[0], -1, dtype=int)
        chunk_size = 2048
        for start in range(0, feature_matrix.shape[0], chunk_size):
            end = min(start + chunk_size, feature_matrix.shape[0])
            distances = pairwise_distances(
                feature_matrix[start:end], self.core_samples_, self.distance
            )
            nearest = np.argmin(distances, axis=1)
            nearest_distances = distances[np.arange(len(nearest)), nearest]
            assigned = np.where(nearest_distances <= self.eps, self.core_labels_[nearest], -1)
            labels[start:end] = assigned
        return labels

    def fit_predict(self, feature_matrix):
        return self.fit(feature_matrix)
