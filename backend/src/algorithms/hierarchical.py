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

    for _ in range(n_rows - 1):
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
            centroid_shifts = centroids - new_centroid
            centroid_distances = np.sqrt(np.sum(centroid_shifts * centroid_shifts, axis=1))
            scale = np.sqrt(2.0 * new_size * sizes / (new_size + sizes))
            updated = scale * centroid_distances
            updated[index_a] = np.inf
            updated[index_b] = np.inf
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

    merge_array = np.array(merge_matrix, dtype=float).reshape(-1, 4)
    labels = cut_dendrogram(merge_array, n_clusters)
    return merge_array, labels


def cut_dendrogram(merge_matrix, n_clusters):
    merge_matrix = np.asarray(merge_matrix, dtype=float)
    if merge_matrix.ndim != 2 or merge_matrix.shape[0] == 0:
        return np.zeros(0, dtype=int)

    n_rows = merge_matrix.shape[0] + 1
    n_clusters = int(n_clusters)
    merges_to_apply = max(n_rows - n_clusters, 0)

    parent = list(range(n_rows))

    for row in range(merges_to_apply):
        index_a = int(merge_matrix[row, 0])
        index_b = int(merge_matrix[row, 1])

        root_a = index_a
        while parent[root_a] != root_a:
            parent[root_a] = parent[parent[root_a]]
            root_a = parent[root_a]

        root_b = index_b
        while parent[root_b] != root_b:
            parent[root_b] = parent[parent[root_b]]
            root_b = parent[root_b]

        if root_a != root_b:
            parent[root_b] = root_a

    labels = np.zeros(n_rows, dtype=int)
    roots = []
    for node in range(n_rows):
        root = node
        while parent[root] != root:
            root = parent[root]
        if root not in roots:
            roots.append(root)
        labels[node] = roots.index(root)
    return labels
