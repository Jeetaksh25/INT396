import numpy as np


class KMedoidsCustom:
    def __init__(self, n_clusters=6, max_iter=100, random_seed=0):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.random_seed = random_seed
        self.medoid_indices_ = None
        self.medoid_points_ = None
        self.labels_ = None
        self.cost_ = None

    def _assign(self, distances, medoid_indices):
        medoid_distances = distances[:, medoid_indices]
        return np.argmin(medoid_distances, axis=1), float(np.sum(np.min(medoid_distances, axis=1)))

    def _build(self, distances):
        n_rows = distances.shape[0]
        medoids = [int(np.argmin(np.sum(distances, axis=1)))]
        closest = distances[:, medoids[0]].copy()

        while len(medoids) < self.n_clusters:
            best_index = -1
            best_cost = None
            for candidate in range(n_rows):
                if candidate in medoids:
                    continue
                trial_cost = float(np.sum(np.minimum(closest, distances[:, candidate])))
                if best_cost is None or trial_cost < best_cost:
                    best_cost = trial_cost
                    best_index = candidate
            medoids.append(best_index)
            closest = np.minimum(closest, distances[:, best_index])

        return np.array(medoids, dtype=int)

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        n_rows = feature_matrix.shape[0]
        difference = feature_matrix[:, None, :] - feature_matrix[None, :, :]
        distances = np.sqrt(np.sum(difference * difference, axis=2))

        medoids = self._build(distances)
        labels, current_cost = self._assign(distances, medoids)

        for _ in range(self.max_iter):
            best_cost = current_cost
            best_medoids = medoids.copy()
            for position in range(self.n_clusters):
                for candidate in range(n_rows):
                    if candidate in medoids:
                        continue
                    trial = medoids.copy()
                    trial[position] = candidate
                    _, trial_cost = self._assign(distances, trial)
                    if trial_cost < best_cost:
                        best_cost = trial_cost
                        best_medoids = trial
            if best_cost >= current_cost:
                break
            medoids = best_medoids
            current_cost = best_cost

        self.medoid_indices_ = medoids
        self.medoid_points_ = feature_matrix[medoids].copy()
        self.labels_, self.cost_ = self._assign(distances, medoids)
        return self

    def predict(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        difference = feature_matrix[:, None, :] - self.medoid_points_[None, :, :]
        distances = np.sqrt(np.sum(difference * difference, axis=2))
        return np.argmin(distances, axis=1)

    def fit_predict(self, feature_matrix):
        self.fit(feature_matrix)
        return self.labels_
