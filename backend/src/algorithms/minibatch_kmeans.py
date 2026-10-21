import numpy as np

from src.algorithms.distance_metrics import pairwise_distances


class MiniBatchKMeansCustom:
    def __init__(self, n_clusters=6, batch_size=256, max_iter=100, random_seed=0):
        self.n_clusters = n_clusters
        self.batch_size = batch_size
        self.max_iter = max_iter
        self.random_seed = random_seed
        self.centroids_ = None
        self.labels_ = None
        self.inertia_ = None

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        n_rows = feature_matrix.shape[0]
        generator = np.random.default_rng(self.random_seed)

        sample_size = min(n_rows, max(self.n_clusters, self.batch_size))
        sample_indices = generator.choice(n_rows, size=sample_size, replace=False)
        self.centroids_ = feature_matrix[sample_indices][: self.n_clusters].copy()

        for _ in range(self.max_iter):
            batch_indices = generator.choice(n_rows, size=min(n_rows, self.batch_size), replace=False)
            batch = feature_matrix[batch_indices]
            distances = pairwise_distances(batch, self.centroids_, "euclidean")
            batch_labels = np.argmin(distances, axis=1)

            for cluster_id in range(self.n_clusters):
                members = batch[batch_labels == cluster_id]
                if members.shape[0] > 0:
                    count = members.shape[0]
                    batch_mean = np.mean(members, axis=0)
                    self.centroids_[cluster_id] = self.centroids_[cluster_id] + (batch_mean - self.centroids_[cluster_id]) / (1.0 + count)

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
