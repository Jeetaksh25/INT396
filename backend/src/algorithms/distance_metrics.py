import numpy as np


def euclidean_distance(vector_a, vector_b):
    vector_a = np.asarray(vector_a, dtype=float)
    vector_b = np.asarray(vector_b, dtype=float)
    difference = vector_a - vector_b
    return float(np.sqrt(np.sum(difference * difference)))


def manhattan_distance(vector_a, vector_b):
    vector_a = np.asarray(vector_a, dtype=float)
    vector_b = np.asarray(vector_b, dtype=float)
    return float(np.sum(np.abs(vector_a - vector_b)))


def cosine_similarity(vector_a, vector_b):
    vector_a = np.asarray(vector_a, dtype=float)
    vector_b = np.asarray(vector_b, dtype=float)
    norm_a = float(np.sqrt(np.sum(vector_a * vector_a)))
    norm_b = float(np.sqrt(np.sum(vector_b * vector_b)))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vector_a, vector_b) / (norm_a * norm_b))


def cosine_distance(vector_a, vector_b):
    return 1.0 - cosine_similarity(vector_a, vector_b)


def pairwise_distances(matrix_a, matrix_b, metric="euclidean"):
    matrix_a = np.asarray(matrix_a, dtype=float)
    matrix_b = np.asarray(matrix_b, dtype=float)
    if matrix_a.ndim == 1:
        matrix_a = matrix_a.reshape(1, -1)
    if matrix_b.ndim == 1:
        matrix_b = matrix_b.reshape(1, -1)

    if metric == "euclidean":
        squared_a = np.sum(matrix_a * matrix_a, axis=1)
        squared_b = np.sum(matrix_b * matrix_b, axis=1)
        dot_products = matrix_a @ matrix_b.T
        squared_distances = squared_a[:, None] + squared_b[None, :] - 2.0 * dot_products
        return np.sqrt(np.maximum(squared_distances, 0.0))

    if metric == "manhattan":
        return np.sum(np.abs(matrix_a[:, None, :] - matrix_b[None, :, :]), axis=2)

    if metric == "cosine":
        dot_products = matrix_a @ matrix_b.T
        norm_a = np.sqrt(np.sum(matrix_a * matrix_a, axis=1))
        norm_b = np.sqrt(np.sum(matrix_b * matrix_b, axis=1))
        denominators = norm_a[:, None] * norm_b[None, :]
        similarities = np.zeros_like(dot_products)
        nonzero = denominators > 0.0
        similarities[nonzero] = dot_products[nonzero] / denominators[nonzero]
        return 1.0 - similarities

    raise ValueError("unknown metric: " + str(metric))
