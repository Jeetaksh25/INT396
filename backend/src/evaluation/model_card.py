import json

import numpy as np
import pandas as pd

import config


MODEL_SPECS = [
    {
        "key": "kmeans",
        "name": "k-Means",
        "unit": "Unit II",
        "family": "Partition clustering",
        "score": "Euclidean distance to assigned centroid",
        "hyperparameters": {
            "n_clusters": config.KMEANS_CLUSTERS,
            "init": "kmeans++",
            "max_iter": 300,
            "tolerance": 1e-4,
            "random_seed": config.RANDOM_SEED,
        },
        "why": "Groups reference-period weather regimes; a reading far from its own regime is suspicious.",
    },
    {
        "key": "dbscan",
        "name": "DBSCAN",
        "unit": "Unit III",
        "family": "Density clustering",
        "score": "1 when the point is noise, otherwise 0",
        "hyperparameters": {
            "eps": config.DBSCAN_EPS,
            "min_samples": config.DBSCAN_MIN_SAMPLES,
            "max_fit_samples": 4000,
            "max_core_samples": 2500,
            "distance": "euclidean",
        },
        "why": "Noise is the definition of an outlier here, so faults need no cluster membership.",
    },
    {
        "key": "pca",
        "name": "PCA reconstruction",
        "unit": "Unit IV",
        "family": "Linear reconstruction",
        "score": "Squared reconstruction error at 90% variance",
        "hyperparameters": {
            "variance_target": config.PCA_VARIANCE_TARGET,
            "solver": "numpy.linalg.eigh on the covariance matrix",
            "centering": "reference-period mean",
        },
        "why": "Extremes run along real variance directions; faults break the correlation structure.",
    },
    {
        "key": "isolation",
        "name": "Isolation Forest",
        "unit": "Unit V",
        "family": "Tree ensemble",
        "score": "2^(-E[h(x)] / c(n)), higher means more isolated",
        "hyperparameters": {
            "n_trees": config.ISOLATION_FOREST_TREES,
            "sub_sample_size": config.ISOLATION_FOREST_SUBSAMPLE,
            "random_seed": config.RANDOM_SEED,
        },
        "why": "Random splits isolate rare readings in few steps, independent of density assumptions.",
    },
    {
        "key": "lof",
        "name": "Local Outlier Factor",
        "unit": "Unit V",
        "family": "Local density",
        "score": "LOF score against the reference neighbourhood",
        "hyperparameters": {
            "n_neighbors": config.LOF_NEIGHBOURS,
            "max_reference_samples": 12000,
            "novelty_mode": True,
        },
        "why": "Catches readings that are sparse relative to their own neighbourhood, not globally.",
    },
]


def per_model_metrics(detections, labels):
    merged = detections.merge(
        labels[
            [
                "station_id",
                "timestamp",
                "sensor_name",
                "is_fault_injected",
                "is_extreme_event",
            ]
        ],
        on=["station_id", "timestamp", "sensor_name"],
        how="left",
    )
    merged["is_fault_injected"] = merged["is_fault_injected"].fillna(0).astype(int)
    merged["is_extreme_event"] = merged["is_extreme_event"].fillna(0).astype(int)
    is_true_anomaly = (
        (merged["is_fault_injected"] == 1) | (merged["is_extreme_event"] == 1)
    ).to_numpy()
    is_fault = (merged["is_fault_injected"] == 1).to_numpy()

    rows = []
    for spec in MODEL_SPECS:
        vote_column = f"{spec['key']}_vote"
        score_column = f"{spec['key']}_score"
        if vote_column not in merged.columns:
            continue
        votes = merged[vote_column].to_numpy() == 1
        true_positive = int(np.sum(votes & is_true_anomaly))
        false_positive = int(np.sum(votes & ~is_true_anomaly))
        false_negative = int(np.sum(~votes & is_true_anomaly))
        precision = true_positive / max(true_positive + false_positive, 1)
        recall = true_positive / max(true_positive + false_negative, 1)
        rows.append(
            {
                "key": spec["key"],
                "name": spec["name"],
                "unit": spec["unit"],
                "family": spec["family"],
                "score": spec["score"],
                "why": spec["why"],
                "hyperparameters": spec["hyperparameters"],
                "vote_rate": round(float(votes.mean()), 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(2 * precision * recall / max(precision + recall, 1e-9), 4),
                "fault_recall": round(float(np.sum(votes & is_fault) / max(is_fault.sum(), 1)), 4),
                "score_mean": round(float(merged[score_column].mean()), 4),
                "score_p99": round(float(np.quantile(merged[score_column], 0.99)), 4),
            }
        )
    return rows


def build_model_card():
    detections = pd.read_csv(config.DETECTIONS_CSV, parse_dates=["timestamp"])
    labels = pd.read_parquet(config.PROCESSED_DIR / "labels.parquet")
    labels["timestamp"] = pd.to_datetime(labels["timestamp"])
    with open(config.METRICS_JSON, "r", encoding="utf-8") as handle:
        metrics = json.load(handle)

    models = per_model_metrics(detections, labels)
    vote_counts = detections["vote_count"].value_counts().sort_index()
    agreement = {
        str(int(vote)): int(count) for vote, count in vote_counts.items()
    }
    total_rows = int(len(detections))
    agreement_share = {
        str(int(vote)): round(float(count) / total_rows, 6)
        for vote, count in vote_counts.items()
    }

    return {
        "generated_at": metrics["generated_at"],
        "task": "Unsupervised sensor fault discovery with fault-versus-extreme separation",
        "supervision": {
            "training_labels_used": 0,
            "label_source": "synthetic injection, evaluation only",
            "guard": "src/features/leakage_guard.py rejects label columns in the model path",
        },
        "dataset": {
            **metrics["dataset"],
            "reference_rows": metrics["diagnostics"]["reference_rows"],
            "reference_fraction": config.REFERENCE_PERIOD_FRACTION,
            "fault_readings": metrics["label_counts"]["fault_readings"],
            "extreme_readings": metrics["label_counts"]["extreme_readings"],
            "fault_coverage": round(
                metrics["label_counts"]["fault_readings"] / total_rows, 6
            ),
            "extreme_coverage": round(
                metrics["label_counts"]["extreme_readings"] / total_rows, 6
            ),
        },
        "consensus": {
            "vote_threshold": config.CONSENSUS_VOTE_THRESHOLD,
            "vote_total": config.CONSENSUS_VOTE_TOTAL,
            "reference_quantile": config.REFERENCE_QUANTILE,
            "agreement_counts": agreement,
            "agreement_share": agreement_share,
            "pca_components": metrics["diagnostics"]["pca_components"],
            "vote_thresholds": metrics["diagnostics"]["vote_thresholds"],
            "reference_vote_rates": metrics["diagnostics"]["vote_rates_reference"],
        },
        "features": {
            "columns": config.FEATURE_COLUMNS,
            "count": len(config.FEATURE_COLUMNS),
            "scaling": "per-station standardisation fitted on the reference period",
        },
        "models": models,
        "detector": metrics["detector"],
        "baseline_range_check": metrics["baseline_range_check"],
        "delta": metrics["delta"],
        "per_fault_type_recall": metrics["per_fault_type_recall"],
        "baseline_per_fault_type_recall": metrics["baseline_per_fault_type_recall"],
        "confusion": metrics["confusion"],
        "event_metrics": metrics["event_metrics"],
        "timing": metrics["timing"],
        "association_rules": {
            "rule_count": metrics["rule_count"],
            "min_support": config.APRIORI_MIN_SUPPORT,
            "min_confidence": config.APRIORI_MIN_CONFIDENCE,
        },
        "runtime": {
            "detector_seconds": metrics["timing"].get("detector_seconds"),
            "discriminator_seconds": metrics["timing"].get("discriminator_seconds"),
            "features_seconds": metrics["timing"].get("features_seconds"),
        },
    }


def save_model_card():
    card = build_model_card()
    target = config.RESULTS_DIR / "model_card.json"
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(card, handle, indent=2, default=str)
    return card


if __name__ == "__main__":
    card = save_model_card()
    print(json.dumps({"models": len(card["models"]), "rows": card["dataset"]["rows"]}, indent=2))
