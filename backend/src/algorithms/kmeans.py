import numpy as np

from src.algorithms.distance_metrics import pairwise_distances


class KMeansCustom:
    def __init__(self, n_clusters=6, init="kmeans++", max_iter=300, tolerance=1e-4, random_seed=0):
        self.n_clusters = n_clusters
        self.init = init
        self.max_iter = max_iter
        self.tolerance = tolerance
        self.random_seed = random_seed
        self.centroids_ = None
        self.labels_ = None
        self.inertia_ = None

    def _initial_centroids(self, feature_matrix):
        n_rows = feature_matrix.shape[0]
        generator = np.random.default_rng(self.random_seed)
        if self.init != "kmeans++":
            indices = generator.choice(n_rows, size=self.n_clusters, replace=False)
            return feature_matrix[indices].copy()

        first_index = int(generator.integers(0, n_rows))
        centroids = [feature_matrix[first_index]]
        closest_squared = np.sum((feature_matrix - centroids[0]) ** 2, axis=1)
        for _ in range(1, self.n_clusters):
            total = float(np.sum(closest_squared))
            if total <= 0.0:
                index = int(generator.integers(0, n_rows))
            else:
                probabilities = closest_squared / total
                index = int(generator.choice(n_rows, p=probabilities))
            centroids.append(feature_matrix[index])
            new_squared = np.sum((feature_matrix - feature_matrix[index]) ** 2, axis=1)
            closest_squared = np.minimum(closest_squared, new_squared)
        return np.array(centroids, dtype=float)

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        n_rows = feature_matrix.shape[0]
        if self.n_clusters > n_rows:
            raise ValueError("n_clusters cannot exceed number of rows")
        self.centroids_ = self._initial_centroids(feature_matrix)

        for _ in range(self.max_iter):
            distances = pairwise_distances(feature_matrix, self.centroids_, "euclidean")
            labels = np.argmin(distances, axis=1)
            previous = self.centroids_.copy()
            reassigned = set()

            for cluster_id in range(self.n_clusters):
                members = feature_matrix[labels == cluster_id]
                if members.shape[0] > 0:
                    self.centroids_[cluster_id] = np.mean(members, axis=0)
                    continue
                row_distances = distances[np.arange(n_rows), labels]
                for candidate in np.argsort(-row_distances):
                    candidate = int(candidate)
                    if candidate in reassigned or labels[candidate] == cluster_id:
                        continue
                    self.centroids_[cluster_id] = feature_matrix[candidate]
                    labels[candidate] = cluster_id
                    reassigned.add(candidate)
                    break

            shift = float(np.max(np.sqrt(np.sum((self.centroids_ - previous) ** 2, axis=1))))
            if shift < self.tolerance:
                break

        final_distances = pairwise_distances(feature_matrix, self.centroids_, "euclidean")
        self.labels_ = np.argmin(final_distances, axis=1)
        self.inertia_ = float(np.sum(np.min(final_distances, axis=1) ** 2))
        return self

    def predict(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        distances = pairwise_distances(feature_matrix, self.centroids_, "euclidean")
        return np.argmin(distances, axis=1)

    def fit_predict(self, feature_matrix):
        self.fit(feature_matrix)
        return self.labels_
