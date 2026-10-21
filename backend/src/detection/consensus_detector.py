import numpy as np
import pandas as pd

import config
from src.algorithms.anomaly_detectors import IsolationForestCustom, LocalOutlierFactorCustom
from src.algorithms.dbscan import DBSCANCustom
from src.algorithms.kmeans import KMeansCustom
from src.algorithms.pca import PCACustom
from src.features.feature_builder import rolling_mean, rolling_std

SCORE_NAMES = ["kmeans", "dbscan", "pca", "isolation", "lof"]


def fit_kmeans_score(reference_matrix, full_matrix):
    model = KMeansCustom(
        n_clusters=config.KMEANS_CLUSTERS,
        init="kmeans++",
        random_seed=config.RANDOM_SEED,
    ).fit(reference_matrix)
    labels = model.predict(full_matrix)
    centroids = model.centroids_[labels]
    distances = np.sqrt(np.sum((full_matrix - centroids) ** 2, axis=1))
    return distances, labels


def fit_dbscan_score(reference_matrix, full_matrix):
    model = DBSCANCustom(eps=config.DBSCAN_EPS, min_samples=config.DBSCAN_MIN_SAMPLES)
    model.fit(reference_matrix)
    full_labels = model.predict(full_matrix)
    noise_scores = (full_labels == -1).astype(float)
    return noise_scores, full_labels


def fit_pca_score(reference_matrix, full_matrix):
    model = PCACustom().fit(reference_matrix)
    cumulative = np.cumsum(model.explained_variance_ratio_)
    n_components = int(np.searchsorted(cumulative, config.PCA_VARIANCE_TARGET) + 1)
    n_components = max(1, min(n_components, len(model.explained_variance_ratio_)))
    errors = model.reconstruction_error(full_matrix, n_components=n_components)
    return errors, n_components


def fit_isolation_score(reference_matrix, full_matrix):
    model = IsolationForestCustom(
        n_trees=config.ISOLATION_FOREST_TREES,
        sub_sample_size=config.ISOLATION_FOREST_SUBSAMPLE,
        random_seed=config.RANDOM_SEED,
    ).fit(reference_matrix)
    scores = model.score_samples(full_matrix)
    return scores, None


def fit_lof_score(reference_matrix, full_matrix):
    model = LocalOutlierFactorCustom(n_neighbors=config.LOF_NEIGHBOURS)
    model.fit(reference_matrix)
    scores = model.score_samples(full_matrix)
    labels = np.where(scores > 1.5, -1, 1)
    return scores, labels


def threshold_from_reference(scores, reference_mask, quantile=None):
    if quantile is None:
        quantile = config.REFERENCE_QUANTILE
    reference_scores = scores if reference_mask is None else scores[reference_mask]
    if len(reference_scores) == 0:
        reference_scores = scores
    unique_values = np.unique(reference_scores)
    if len(unique_values) <= 2 and set(unique_values.tolist()).issubset({0.0, 1.0}):
        return 0.5
    return float(np.quantile(reference_scores, quantile))


def build_bank(reference_matrix):
    kmeans_model = KMeansCustom(
        n_clusters=config.KMEANS_CLUSTERS,
        init="kmeans++",
        random_seed=config.RANDOM_SEED,
    ).fit(reference_matrix)
    dbscan_model = DBSCANCustom(eps=config.DBSCAN_EPS, min_samples=config.DBSCAN_MIN_SAMPLES)
    dbscan_model.fit(reference_matrix)
    pca_model = PCACustom().fit(reference_matrix)
    isolation_model = IsolationForestCustom(
        n_trees=config.ISOLATION_FOREST_TREES,
        sub_sample_size=config.ISOLATION_FOREST_SUBSAMPLE,
        random_seed=config.RANDOM_SEED,
    ).fit(reference_matrix)
    lof_model = LocalOutlierFactorCustom(n_neighbors=config.LOF_NEIGHBOURS).fit(reference_matrix)
    return {
        "kmeans": kmeans_model,
        "dbscan": dbscan_model,
        "pca": pca_model,
        "isolation": isolation_model,
        "lof": lof_model,
    }


def score_with_bank(bank, matrix):
    kmeans_labels = bank["kmeans"].predict(matrix)
    centroids = bank["kmeans"].centroids_[kmeans_labels]
    kmeans_scores = np.sqrt(np.sum((matrix - centroids) ** 2, axis=1))

    dbscan_labels = bank["dbscan"].predict(matrix)
    dbscan_scores = (dbscan_labels == -1).astype(float)

    cumulative = np.cumsum(bank["pca"].explained_variance_ratio_)
    components = int(np.searchsorted(cumulative, config.PCA_VARIANCE_TARGET) + 1)
    components = max(1, min(components, len(bank["pca"].explained_variance_ratio_)))
    pca_scores = bank["pca"].reconstruction_error(matrix, n_components=components)

    scores = {
        "kmeans_score": kmeans_scores,
        "dbscan_score": dbscan_scores,
        "pca_score": pca_scores,
        "isolation_score": bank["isolation"].score_samples(matrix),
        "lof_score": bank["lof"].score_samples(matrix),
    }
    labels = {"kmeans": kmeans_labels, "dbscan": dbscan_labels}
    return scores, labels, components


def fit_consensus(reference_matrix):
    bank = build_bank(reference_matrix)
    reference_scores, _, components = score_with_bank(bank, reference_matrix)
    thresholds = {
        name.replace("_score", "_vote"): threshold_from_reference(scores, None)
        for name, scores in reference_scores.items()
    }
    vote_rates = {
        name.replace("_score", "_vote"): float(
            np.mean(reference_scores[name] > thresholds[name.replace("_score", "_vote")])
        )
        for name in reference_scores
    }
    return {
        "bank": bank,
        "thresholds": thresholds,
        "vote_rates": vote_rates,
        "pca_components": components,
        "reference_rows": int(len(reference_matrix)),
    }


def assemble_detections(features, scores, labels, threshold_map):
    values = features["measured_value"].astype(float)
    local_mean = rolling_mean(values)
    local_std = rolling_std(values).replace(0.0, np.nan).fillna(1.0)
    sensor_deviation = ((values - local_mean) / local_std).fillna(0.0)

    result = features[["station_id", "sensor_name", "timestamp", "measured_value"]].copy()
    result["sensor_deviation"] = sensor_deviation.to_numpy()

    vote_columns = {}
    for name, name_scores in scores.items():
        threshold = threshold_map[name.replace("_score", "_vote")]
        vote_columns[name.replace("_score", "_vote")] = (name_scores > threshold).astype(int)

    vote_matrix = np.column_stack(list(vote_columns.values()))
    vote_count = vote_matrix.sum(axis=1)
    anomaly_score = vote_count / config.CONSENSUS_VOTE_TOTAL
    is_anomaly = (vote_count >= config.CONSENSUS_VOTE_THRESHOLD).astype(int)

    anomaly_flags = pd.Series(is_anomaly, index=result.index)
    group_key = result["station_id"].astype(str) + "|" + result["sensor_name"].astype(str)
    local_deviation = result["sensor_deviation"].abs()
    local_flag = (
        (anomaly_flags == 1) & (local_deviation > config.NEIGHBOUR_DEVIATION_THRESHOLD)
    ).astype(int)
    per_group_anomalies = anomaly_flags.groupby(group_key).transform("sum")
    per_group_flagged = local_flag.groupby(group_key).transform("sum")
    fallback = (per_group_anomalies > 0) & (per_group_flagged == 0)
    is_local_anomaly = (anomaly_flags == 1) & ((local_flag == 1) | fallback)

    result["is_local_anomaly"] = is_local_anomaly.astype(int)
    for name, name_scores in scores.items():
        result[name] = name_scores
    for name, vote in vote_columns.items():
        result[name] = vote
    result["vote_count"] = vote_count
    result["anomaly_score"] = anomaly_score
    result["is_anomaly"] = is_anomaly
    result["kmeans_cluster"] = labels["kmeans"]
    result["dbscan_cluster"] = labels["dbscan"]
    return result


def compute_consensus(features, matrix, reference_mask):
    reference_matrix = matrix[reference_mask]
    fitted = fit_consensus(reference_matrix)
    scores, labels, components = score_with_bank(fitted["bank"], matrix)
    result = assemble_detections(features, scores, labels, fitted["thresholds"])
    result["pca_components"] = components

    dbscan_labels = labels["dbscan"]
    diagnostics = {
        "vote_thresholds": dict(fitted["thresholds"]),
        "vote_rates_reference": dict(fitted["vote_rates"]),
        "pca_components": int(components),
        "dbscan_noise_percent": float(100.0 * np.mean(dbscan_labels == -1)),
        "lof_outlier_percent": float(
            100.0 * np.mean(scores["lof_score"] > fitted["thresholds"]["lof_vote"])
        ),
        "reference_rows": int(fitted["reference_rows"]),
        "total_rows": int(len(matrix)),
    }
    return result, diagnostics
