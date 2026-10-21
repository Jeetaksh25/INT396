import numpy as np


def _initial_distance_matrix(feature_matrix):
    difference = feature_matrix[:, None, :] - feature_matrix[None, :, :]
    return np.sqrt(np.sum(difference * difference, axis=2))


def agglomerative_clustering(feature_matrix, linkage="ward", n_clusters=8):
    feature_matrix = np.asarray(feature_matrix, dtype=float)
    n_rows = feature_matrix.shape[0]
    n_clusters = max(1, min(int(n_clusters), n_rows))

    distances = _initial_distance_matrix(feature_matrix)
    active = np.ones(n_rows, dtype=bool)
    sizes = np.ones(n_rows, dtype=float)
    centroids = feature_matrix.copy()

    merge_matrix = []

    for _ in range(n_rows - n_clusters):
        masked = np.where(active[:, None] & active[None, :], distances, np.inf)
        np.fill_diagonal(masked, np.inf)
        flat_index = int(np.argmin(masked))
        index_a, index_b = divmod(flat_index, n_rows)
        if index_a > index_b:
            index_a, index_b = index_b, index_a

        merge_distance = float(distances[index_a, index_b])
        merge_matrix.append([float(index_a), float(index_b), merge_distance, float(sizes[index_a] + sizes[index_b])])

        if linkage == "single":
            updated = np.minimum(distances[index_a], distances[index_b])
        elif linkage == "complete":
            updated = np.maximum(distances[index_a], distances[index_b])
        elif linkage == "average":
            updated = (sizes[index_a] * distances[index_a] + sizes[index_b] * distances[index_b]) / (sizes[index_a] + sizes[index_b])
        elif linkage == "ward":
            new_size = sizes[index_a] + sizes[index_b]
            new_centroid = (sizes[index_a] * centroids[index_a] + sizes[index_b] * centroids[index_b]) / new_size
            updated = np.copy(distances[index_a])
            for other in range(n_rows):
                if not active[other] or other in (index_a, index_b):
                    continue
                other_distance = float(np.sqrt(np.sum((centroids[other] - new_centroid) ** 2)))
                updated[other] = np.sqrt(2.0 * new_size * sizes[other] / (new_size + sizes[other])) * other_distance
            centroids[index_a] = new_centroid
        else:
            raise ValueError("unknown linkage: " + str(linkage))

        distances[index_a, :] = updated
        distances[:, index_a] = updated
        distances[index_a, index_a] = 0.0
        active[index_b] = False
        distances[index_b, :] = np.inf
        distances[:, index_b] = np.inf
        sizes[index_a] += sizes[index_b]

    merge_array = np.array(merge_matrix, dtype=float) if merge_matrix else np.zeros((0, 4))
    labels = cut_dendrogram(merge_array, n_clusters)
    return merge_array, labels


def cut_dendrogram(merge_matrix, n_clusters):
    merge_matrix = np.asarray(merge_matrix, dtype=float)
    if merge_matrix.ndim != 2 or merge_matrix.shape[0] == 0:
        return np.zeros(0, dtype=int)

    n_clusters = int(n_clusters)
    merge_count = merge_matrix.shape[0]
    largest_index = int(max(np.max(merge_matrix[:, 0]), np.max(merge_matrix[:, 1])))
    if largest_index <= merge_count:
        n_rows = merge_count + 1
    else:
        n_rows = merge_count + n_clusters

    merges_to_apply = min(n_rows - n_clusters, merge_count)
    merges_to_apply = max(merges_to_apply, 0)

    parent = list(range(n_rows))

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left, right):
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for row in range(merge_matrix.shape[0]):
        index_a = int(merge_matrix[row, 0])
        index_b = int(merge_matrix[row, 1])
        union(index_a, index_b)

    roots = [find(node) for node in range(n_rows)]
    order = []
    for root in roots:
        if root not in order:
            order.append(root)

    labels = np.zeros(n_rows, dtype=int)
    for node in range(n_rows):
        labels[node] = order.index(roots[node])
    return labels
