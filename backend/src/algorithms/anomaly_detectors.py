import io
import json
import math
import os

import numpy as np

from src.algorithms.distance_metrics import pairwise_distances


def _harmonic(number):
    if number <= 0:
        return 0.0
    return float(np.sum(1.0 / np.arange(1, number + 1)))


def _average_path_length(size):
    if size <= 1:
        return 1.0
    return 2.0 * _harmonic(size - 1) - 2.0 * (size - 1) / size


def _average_path_length_table(maximum):
    table = np.ones(maximum + 1, dtype=float)
    for size in range(2, maximum + 1):
        table[size] = _average_path_length(size)
    return table


class IsolationForestCustom:
    def __init__(self, n_trees=100, sub_sample_size=256, random_seed=0):
        self.n_trees = n_trees
        self.sub_sample_size = sub_sample_size
        self.random_seed = random_seed
        self.trees_ = []
        self.normalizer_ = 1.0
        self.average_path_table_ = None

    def _build_tree(self, values, depth, depth_limit, generator):
        rows = values.shape[0]
        if depth >= depth_limit or rows <= 1:
            return {"feature": -1, "split": 0.0, "left": None, "right": None, "size": rows}

        features = values.shape[1]
        candidate_features = list(range(features))
        generator.shuffle(candidate_features)
        chosen_feature = None
        minimum_value = maximum_value = 0.0
        for feature in candidate_features:
            column = values[:, feature]
            column_minimum = float(column.min())
            column_maximum = float(column.max())
            if column_maximum > column_minimum:
                chosen_feature = feature
                minimum_value = column_minimum
                maximum_value = column_maximum
                break

        if chosen_feature is None:
            return {"feature": -1, "split": 0.0, "left": None, "right": None, "size": rows}

        split_value = float(generator.uniform(minimum_value, maximum_value))
        left_mask = values[:, chosen_feature] < split_value
        if not np.any(left_mask) or np.all(left_mask):
            return {"feature": -1, "split": 0.0, "left": None, "right": None, "size": rows}

        return {
            "feature": chosen_feature,
            "split": split_value,
            "left": self._build_tree(values[left_mask], depth + 1, depth_limit, generator),
            "right": self._build_tree(values[~left_mask], depth + 1, depth_limit, generator),
            "size": rows,
        }

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
            sizes.append(float(node["size"]))
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
    def __init__(self, n_neighbors=20, max_reference_samples=4000):
        self.n_neighbors = n_neighbors
        self.max_reference_samples = max_reference_samples
        self.reference_ = None
        self.k_distances_ = None
        self.reachability_ = None
        self.lrd_ = None
        self.lof_ = None

    def fit(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        n_rows = feature_matrix.shape[0]
        if n_rows > self.max_reference_samples:
            step = max(1, n_rows // self.max_reference_samples)
            indices = np.arange(0, n_rows, step)[: self.max_reference_samples]
            reference = feature_matrix[indices]
        else:
            reference = feature_matrix

        self.reference_ = reference
        neighbour_count = min(self.n_neighbors, len(reference))
        distances = pairwise_distances(reference, reference, "euclidean")
        np.fill_diagonal(distances, np.inf)
        sorted_distances = np.sort(distances, axis=1)
        self.k_distances_ = sorted_distances[:, neighbour_count - 1]
        neighbour_indices = np.argpartition(distances, neighbour_count - 1, axis=1)[
            :, :neighbour_count
        ]
        neighbour_distances = np.take_along_axis(distances, neighbour_indices, axis=1)
        reachability = np.maximum(
            neighbour_distances, self.k_distances_[neighbour_indices]
        )
        self.reachability_ = reachability
        self.neighbour_indices_ = neighbour_indices
        mean_reachability = np.mean(reachability, axis=1)
        self.lrd_ = 1.0 / np.maximum(mean_reachability, 1e-12)
        self.lof_ = np.mean(self.lrd_[neighbour_indices] / self.lrd_[:, None], axis=1)
        return self

    def score_samples(self, feature_matrix):
        feature_matrix = np.asarray(feature_matrix, dtype=float)
        neighbour_count = min(self.n_neighbors, len(self.reference_))
        scores = np.zeros(feature_matrix.shape[0], dtype=float)
        chunk_size = 2048
        for start in range(0, feature_matrix.shape[0], chunk_size):
            end = min(start + chunk_size, feature_matrix.shape[0])
            chunk = feature_matrix[start:end]
            distances = pairwise_distances(chunk, self.reference_, "euclidean")
            neighbour_indices = np.argpartition(distances, neighbour_count - 1, axis=1)[
                :, :neighbour_count
            ]
            neighbour_distances = np.take_along_axis(distances, neighbour_indices, axis=1)
            reachability = np.maximum(
                neighbour_distances, self.k_distances_[neighbour_indices]
            )
            mean_reachability = np.mean(reachability, axis=1)
            lrd = 1.0 / np.maximum(mean_reachability, 1e-12)
            lof = np.mean(self.lrd_[neighbour_indices] / lrd[:, None], axis=1)
            scores[start:end] = lof
        return scores

    def fit_predict(self, feature_matrix):
        self.fit(feature_matrix)
        scores = self.score_samples(feature_matrix)
        labels = np.where(scores > 1.5, -1, 1)
        return labels, -scores
