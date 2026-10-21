import numpy as np

import config
from src.algorithms.distance_metrics import (
    cosine_distance,
    cosine_similarity,
    euclidean_distance,
    manhattan_distance,
)
from src.algorithms.dbscan import DBSCANCustom
from src.algorithms.kmeans import KMeansCustom
from src.algorithms.pca import PCACustom


def test_distance_metrics():
    vector_a = np.array([1.0, 2.0, 3.0])
    vector_b = np.array([4.0, 6.0, 3.0])
    assert abs(euclidean_distance(vector_a, vector_b) - 5.0) < 1e-9
    assert abs(manhattan_distance(vector_a, vector_b) - 7.0) < 1e-9
    assert abs(cosine_similarity(vector_a, vector_a) - 1.0) < 1e-9
    assert abs(cosine_distance(vector_a, vector_a)) < 1e-9
    assert cosine_similarity(np.zeros(3), vector_a) == 0.0
    print("distance metrics ok")


def test_kmeans_recovers_clusters():
    generator = np.random.default_rng(3)
    matrix_a = generator.normal(0.0, 0.4, (120, 3))
    matrix_b = generator.normal(6.0, 0.4, (120, 3))
    feature_matrix = np.vstack([matrix_a, matrix_b])
    model = KMeansCustom(n_clusters=2, init="kmeans++", random_seed=1).fit(feature_matrix)
    assert len(np.unique(model.labels_)) == 2
    assert model.inertia_ < 400.0
    first_cluster = model.labels_[:120]
    second_cluster = model.labels_[120:]
    assert np.all(first_cluster == first_cluster[0])
    assert np.all(second_cluster == second_cluster[0])
    assert first_cluster[0] != second_cluster[0]
    print("kmeans ok", round(model.inertia_, 2))


def test_pca_reconstruction():
    generator = np.random.default_rng(7)
    feature_matrix = generator.normal(0.0, 1.0, (200, 4))
    model = PCACustom().fit(feature_matrix)
    errors = model.reconstruction_error(feature_matrix)
    assert errors.mean() < 1e-20
    reduced = model.transform(feature_matrix, n_components=2)
    assert reduced.shape == (200, 2)
    reconstructed = model.inverse_transform(reduced, n_components=2)
    assert reconstructed.shape == feature_matrix.shape
    print("pca ok", round(float(errors.mean()), 24))


def test_dbscan_finds_noise():
    generator = np.random.default_rng(11)
    matrix_a = generator.normal(0.0, 0.2, (80, 2))
    matrix_b = generator.normal(8.0, 0.2, (80, 2))
    feature_matrix = np.vstack([matrix_a, matrix_b, np.array([[40.0, 40.0]])])
    labels = DBSCANCustom(eps=0.8, min_samples=5).fit_predict(feature_matrix)
    assert labels[-1] == -1
    assert len(set(labels[:-1])) == 2
    print("dbscan ok")


def test_physical_limits():
    assert config.PHYSICAL_LIMITS["humidity"] == (0.0, 100.0)
    assert config.PHYSICAL_LIMITS["temperature"][0] < 0.0
    print("config ok")


if __name__ == "__main__":
    test_distance_metrics()
    test_kmeans_recovers_clusters()
    test_pca_reconstruction()
    test_dbscan_finds_noise()
    test_physical_limits()
    print("all tests passed")
