import math

import numpy as np

from src.algorithms.distance_metrics import pairwise_distances


def _harmonic(number):
    if number <= 0:
        return 0.0
    total = 0.0
    for value in range(1, number + 1):
        total += 1.0 / value
    return total


def _average_path_length(size):
    size = float(size)
    if size <= 1.0:
        return 1.0
    if size == 2.0:
        return 1.0
    return 2.0 * _harmonic(int(size) - 1) - 2.0 * (size - 1.0) / size


def _average_path_length_table(max_size):
    harmonic = np.zeros(max_size + 2)
    for value in range(1, max_size + 2):
        harmonic[value] = harmonic[value - 1] + 1.0 / value
    sizes = np.arange(max_size + 2, dtype=float)
    table = np.zeros(max_size + 2)
    table[0] = 1.0
    table[1] = 1.0
    if max_size + 1 >= 2:
        table[2:] = 2.0 * harmonic[1:-1] - 2.0 * (sizes[2:] - 1.0) / sizes[2:]
    return table


class IsolationForestCustom:
    def __init__(self, n_trees=100, sub_sample_size=256, random_seed=0):
        self.n_trees = n_trees
        self.sub_sample_size = sub_sample_size
        self.random_seed = random_seed
        self.trees_ = []
        self.normalizer_ = 1.0
        self.average_path_table_ = _average_path_length_table(1)

    def _build_tree(self, points, depth, depth_limit, generator):
        size = points.shape[0]
        if depth >= depth_limit or size <= 1:
            return {"feature": -1, "split": 0.0, "left": None, "right": None, "size": size}

        feature_ranges = np.max(points, axis=0) - np.min(points, axis=0)
        candidates = np.flatnonzero(feature_ranges > 0.0)
        if candidates.shape[0] == 0:
            return {"feature": -1, "split": 0.0, "left": None, "right": None, "size": size}

        feature = int(generator.choice(candidates))
        low = float(np.min(points[:, feature]))
        high = float(np.max(points[:, feature]))
        split = float(generator.uniform(low, high))

        left_mask = points[:, feature] < split
        if not np.any(left_mask) or np.all(left_mask):
            split = float(np.median(points[:, feature]))
            left_mask = points[:, feature] < split
            if not np.any(left_mask) or np.all(left_mask):
                return {"feature": -1, "split": 0.0, "left": None, "right": None, "size": size}

        left_tree = self._build_tree(points[left_mask], depth + 1, depth_limit, generator)
        right_tree = self._build_tree(points[~left_mask], depth + 1, depth_limit, generator)
        return {"feature": feature, "split": split, "left": left_tree, "right": right_tree, "size": size}

    def _flatten_tree(self, tree):
        features = []
        splits = []
        left_children = []
        right_children = []
        sizes = []

        stack = [(tree, -1)]
        while stack:
            node, parent = stack.pop()
            index = len(features)
            features.append(node["feature"])
            splits.append(node["split"])
            sizes.append(node["size"])
            left_children.append(-1)
            right_children.append(-1)

            if parent >= 0:
                if left_children[parent] == -1:
                    left_children[parent] = index
                else:
                    right_children[parent] = index

            if node["feature"] >= 0:
                stack.append((node["right"], index))
                stack.append((node["left"], index))

        return (
            np.array(features, dtype=np.int64),
            np.array(splits, dtype=float),
            np.array(left_children, dtype=np.int64),
            np.array(right_children, dtype=np.int64),
            np.array(sizes, dtype=float),
        )

    def _path_lengths(self, flat_tree, feature_matrix):
        features, splits, left_children, right_children, sizes = flat_tree
        n_rows = feature_matrix.shape[0]
        nodes = np.zeros(n_rows, dtype=np.int64)
        depths = np.zeros(n_rows, dtype=float)
        active = np.ones(n_rows, dtype=bool)

        while np.any(active):
            active_rows = np.flatnonzero(active)
            active_nodes = nodes[active_rows]
            node_features = features[active_nodes]
            is_leaf = node_features < 0
            go_left = np.zeros(active_rows.shape[0], dtype=bool)
            internal = ~is_leaf
            if np.any(internal):
                internal_rows = active_rows[internal]
                internal_nodes = active_nodes[internal]
                values = feature_matrix[internal_rows, features[internal_nodes]]
                go_left[internal] = values < splits[internal_nodes]

            next_nodes = np.where(
                go_left,
                left_children[active_nodes],
                right_children[active_nodes],
            )
            next_nodes = np.where(is_leaf, active_nodes, next_nodes)
            depths[active_rows] = depths[active_rows] + np.where(is_leaf, 0.0, 1.0)
            nodes[active_rows] = next_nodes
            active[active_rows] = ~is_leaf

        leaf_sizes = sizes[nodes].astype(np.int64)
        return depths + self.average_path_table_[leaf_sizes]

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        n_rows = feature_matrix.shape[0]
        generator = np.random.default_rng(self.random_seed)
        sample_size = min(self.sub_sample_size, n_rows)
        depth_limit = int(math.ceil(math.log2(max(sample_size, 2))))
        self.normalizer_ = _average_path_length(sample_size)
        self.average_path_table_ = _average_path_length_table(sample_size + 1)

        self.trees_ = []
        for _ in range(self.n_trees):
            indices = generator.choice(n_rows, size=sample_size, replace=False)
            tree = self._build_tree(feature_matrix[indices], 0, depth_limit, generator)
            self.trees_.append(self._flatten_tree(tree))
        return self

    def _mean_path_length(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        totals = np.zeros(feature_matrix.shape[0], dtype=float)
        for flat_tree in self.trees_:
            totals += self._path_lengths(flat_tree, feature_matrix)
        return totals / max(len(self.trees_), 1)

    def score_samples(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        mean_depths = self._mean_path_length(feature_matrix)
        normalizer = self.normalizer_ if self.normalizer_ > 0.0 else 1.0
        return np.power(2.0, -mean_depths / normalizer)


class LocalOutlierFactorCustom:
    def __init__(self, n_neighbors=20):
        self.n_neighbors = n_neighbors
        self.neighbour_indices_ = None
        self.k_distances_ = None
        self.lrd_ = None
        self.lof_ = None

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        n_rows = feature_matrix.shape[0]
        neighbours_count = min(self.n_neighbors, max(n_rows - 1, 1))

        neighbour_indices = np.zeros((n_rows, neighbours_count), dtype=np.int64)
        neighbour_distances = np.zeros((n_rows, neighbours_count), dtype=float)

        chunk_size = 512
        for start in range(0, n_rows, chunk_size):
            stop = min(start + chunk_size, n_rows)
            chunk = pairwise_distances(feature_matrix[start:stop], feature_matrix, "euclidean")
            for offset in range(stop - start):
                row = chunk[offset]
                order = np.argsort(row, kind="stable")
                if order[0] == start + offset:
                    order = order[1:]
                else:
                    order = order[order != start + offset]
                selected = order[:neighbours_count]
                neighbour_indices[start + offset] = selected
                neighbour_distances[start + offset] = row[selected]

        k_distances = neighbour_distances[:, -1]

        reachability = np.maximum(neighbour_distances, k_distances[neighbour_indices])
        reachability_mean = np.mean(reachability, axis=1)
        lrd = 1.0 / np.maximum(reachability_mean, 1e-12)

        neighbour_lrd = lrd[neighbour_indices]
        self.lof_ = np.mean(neighbour_lrd, axis=1) / np.maximum(lrd, 1e-12)

        self.neighbour_indices_ = neighbour_indices
        self.k_distances_ = k_distances
        self.lrd_ = lrd
        return self

    def fit_predict(self, feature_matrix):
        self.fit(feature_matrix)
        labels = np.where(self.lof_ > 1.5, -1, 1)
        return labels, -self.lof_
