import numpy as np

from src.algorithms.distance_metrics import pairwise_distances


class DBSCANCustom:
    def __init__(self, eps=1.0, min_samples=5, distance="euclidean"):
        self.eps = eps
        self.min_samples = min_samples
        self.distance = distance

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        n_rows = feature_matrix.shape[0]
        distances = pairwise_distances(feature_matrix, feature_matrix, self.distance)
        neighbours = distances <= self.eps
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

    def fit_predict(self, feature_matrix):
        return self.fit(feature_matrix)
