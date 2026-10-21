import numpy as np

from src.algorithms.distance_metrics import pairwise_distances
from src.algorithms.kmeans import KMeansCustom


def within_cluster_sum_of_squares(labels, feature_matrix, centroids):
    labels = np.asarray(labels)
    feature_matrix = np.asarray(feature_matrix, dtype=float)
    centroids = np.asarray(centroids, dtype=float)
    total = 0.0
    for cluster_id in range(centroids.shape[0]):
        members = feature_matrix[labels == cluster_id]
        if members.shape[0] == 0:
            continue
        difference = members - centroids[cluster_id]
        total += float(np.sum(difference * difference))
    return total


def silhouette_coefficient(feature_matrix, labels):
    feature_matrix = np.asarray(feature_matrix, dtype=float)
    labels = np.asarray(labels)
    valid_mask = labels != -1
    points = feature_matrix[valid_mask]
    point_labels = labels[valid_mask]
    unique_labels = np.unique(point_labels)

    if points.shape[0] < 2 or unique_labels.shape[0] < 2:
        return 0.0

    if points.shape[0] > 5000:
        positions = np.linspace(0, points.shape[0] - 1, 5000).astype(int)
        points = points[positions]
        point_labels = point_labels[positions]
        unique_labels = np.unique(point_labels)
        if unique_labels.shape[0] < 2:
            return 0.0

    distances = pairwise_distances(points, points, "euclidean")
    n_points = points.shape[0]

    mean_to_cluster = np.zeros((n_points, unique_labels.shape[0]))
    for position, cluster_id in enumerate(unique_labels):
        member_mask = point_labels == cluster_id
        count = int(np.sum(member_mask))
        sums = np.sum(distances[:, member_mask], axis=1)
        if count > 1:
            mean_to_cluster[:, position] = sums / (count - 1)
        else:
            mean_to_cluster[:, position] = sums / count

    own_positions = np.searchsorted(unique_labels, point_labels)
    own_mean = mean_to_cluster[np.arange(n_points), own_positions]

    other_mean = mean_to_cluster.copy()
    other_mean[np.arange(n_points), own_positions] = np.inf
    nearest_other = np.min(other_mean, axis=1)

    denominator = np.maximum(own_mean, nearest_other)
    silhouette_values = np.zeros(n_points)
    nonzero = denominator > 0.0
    silhouette_values[nonzero] = (nearest_other[nonzero] - own_mean[nonzero]) / denominator[nonzero]
    return float(np.mean(silhouette_values))


def davies_bouldin_index(feature_matrix, labels):
    feature_matrix = np.asarray(feature_matrix, dtype=float)
    labels = np.asarray(labels)
    valid_mask = labels != -1
    points = feature_matrix[valid_mask]
    point_labels = labels[valid_mask]
    unique_labels = np.unique(point_labels)

    if unique_labels.shape[0] < 2:
        return 0.0

    centroids = []
    scatters = []
    for cluster_id in unique_labels:
        members = points[point_labels == cluster_id]
        centroid = np.mean(members, axis=0)
        centroids.append(centroid)
        scatters.append(float(np.mean(np.sqrt(np.sum((members - centroid) ** 2, axis=1)))))

    centroids = np.array(centroids)
    scatters = np.array(scatters)
    centroid_distances = pairwise_distances(centroids, centroids, "euclidean")

    n_clusters = unique_labels.shape[0]
    ratios = np.zeros((n_clusters, n_clusters))
    for i in range(n_clusters):
        for j in range(n_clusters):
            if i == j:
                continue
            if centroid_distances[i, j] == 0.0:
                ratios[i, j] = 0.0
            else:
                ratios[i, j] = (scatters[i] + scatters[j]) / centroid_distances[i, j]

    return float(np.mean(np.max(ratios, axis=1)))


def elbow_curve(feature_matrix, k_values, random_seed=0):
    feature_matrix = np.asarray(feature_matrix, dtype=float)
    curve = {}
    for k in k_values:
        model = KMeansCustom(n_clusters=int(k), random_seed=random_seed)
        model.fit(feature_matrix)
        curve[int(k)] = float(model.inertia_)
    return curve
