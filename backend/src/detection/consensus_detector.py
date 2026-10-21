import numpy as np

import config
from src.algorithms.anomaly_detectors import IsolationForestCustom, LocalOutlierFactorCustom
from src.algorithms.dbscan import DBSCANCustom
from src.algorithms.kmeans import KMeansCustom
from src.algorithms.pca import PCACustom
from src.features.feature_builder import rolling_mean, rolling_std


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


def threshold_from_reference(scores, reference_mask, quantile=config.REFERENCE_QUANTILE):
    reference_scores = scores[reference_mask]
    if len(reference_scores) == 0:
        return float(np.quantile(scores, quantile))
    return float(np.quantile(reference_scores, quantile))


def compute_consensus(features, matrix, reference_mask):
    reference_matrix = matrix[reference_mask]

    kmeans_scores, kmeans_labels = fit_kmeans_score(reference_matrix, matrix)
    dbscan_scores, dbscan_labels = fit_dbscan_score(reference_matrix, matrix)
    pca_scores, pca_components = fit_pca_score(reference_matrix, matrix)
    isolation_scores, _ = fit_isolation_score(reference_matrix, matrix)
    lof_scores, lof_labels = fit_lof_score(reference_matrix, matrix)

    score_columns = {
        "kmeans_score": kmeans_scores,
        "dbscan_score": dbscan_scores,
        "pca_score": pca_scores,
        "isolation_score": isolation_scores,
        "lof_score": lof_scores,
    }

    vote_columns = {}
    for score_name, scores in score_columns.items():
        threshold = threshold_from_reference(scores, reference_mask)
        vote = (scores > threshold).astype(int)
        vote_columns[score_name.replace("_score", "_vote")] = vote

    vote_matrix = np.column_stack(list(vote_columns.values()))
    vote_count = vote_matrix.sum(axis=1)
    anomaly_score = vote_count / config.CONSENSUS_VOTE_TOTAL
    is_anomaly = (vote_count >= config.CONSENSUS_VOTE_THRESHOLD).astype(int)

    values = features["measured_value"].astype(float)
    local_mean = rolling_mean(values)
    local_std = rolling_std(values).replace(0.0, np.nan).fillna(1.0)
    sensor_deviation = (values - local_mean) / local_std

    result = features[["station_id", "sensor_name", "timestamp", "measured_value"]].copy()
    result["sensor_deviation"] = sensor_deviation.fillna(0.0)

    anomaly_flags = pd.Series(is_anomaly, index=result.index)
    group_key = result["station_id"].astype(str) + "|" + result["sensor_name"].astype(str)
    deviation_threshold = config.NEIGHBOUR_DEVIATION_THRESHOLD
    local_deviation = result["sensor_deviation"].abs()
    local_flag = ((anomaly_flags == 1) & (local_deviation > deviation_threshold)).astype(int)
    per_group_anomalies = anomaly_flags.groupby(group_key).transform("sum")
    per_group_flagged = local_flag.groupby(group_key).transform("sum")
    is_local_anomaly = np.where(
        per_group_anomalies > 0,
        (local_flag == 1) | (per_group_flagged == 0),
        False,
    )
    result["is_local_anomaly"] = is_local_anomaly.astype(int)
    for score_name, scores in score_columns.items():
        result[score_name] = scores
    for vote_name, vote in vote_columns.items():
        result[vote_name] = vote
    result["vote_count"] = vote_count
    result["anomaly_score"] = anomaly_score
    result["is_anomaly"] = is_anomaly
    result["kmeans_cluster"] = kmeans_labels
    result["dbscan_cluster"] = dbscan_labels
    result["pca_components"] = pca_components

    diagnostics = {
        "vote_thresholds": {
            name: threshold_from_reference(scores, reference_mask)
            for name, scores in score_columns.items()
        },
        "vote_rates_reference": {
            name: float(np.mean(vote[reference_mask])) for name, vote in vote_columns.items()
        },
        "pca_components": int(pca_components),
        "dbscan_noise_percent": float(100.0 * np.mean(dbscan_labels == -1)),
        "lof_outlier_percent": float(100.0 * np.mean(lof_labels == -1)),
        "reference_rows": int(reference_mask.sum()),
        "total_rows": int(len(matrix)),
    }
    return result, diagnostics
