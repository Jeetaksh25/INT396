from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SAMPLES_DIR = DATA_DIR / "samples"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

DATASET_CSV = PROCESSED_DIR / "dataset_with_faults.csv"
DATASET_PARQUET = PROCESSED_DIR / "dataset_with_faults.parquet"
DETECTIONS_CSV = RESULTS_DIR / "detections.csv"
EVENTS_CSV = RESULTS_DIR / "detection_events.csv"
STATION_HEALTH_JSON = RESULTS_DIR / "station_health.json"
METRICS_JSON = RESULTS_DIR / "metrics_summary.json"
TIMELINE_JSON = RESULTS_DIR / "network_timeline.json"

RANDOM_SEED = 42

START_DATE = "2023-01-01"
END_DATE = "2023-12-31"
YEAR_HOURS = 8760

STATION_REGISTRY = {
    "DEL": {"name": "Delhi", "latitude": 28.61, "longitude": 77.21},
    "BOM": {"name": "Mumbai", "latitude": 19.08, "longitude": 72.88},
    "MAA": {"name": "Chennai", "latitude": 13.08, "longitude": 80.27},
    "HYD": {"name": "Hyderabad", "latitude": 17.38, "longitude": 78.48},
    "JAI": {"name": "Jaipur", "latitude": 26.92, "longitude": 75.79},
    "CCU": {"name": "Kolkata", "latitude": 22.57, "longitude": 88.36},
    "BLR": {"name": "Bengaluru", "latitude": 12.97, "longitude": 77.59},
    "SLM": {"name": "Shimla", "latitude": 31.10, "longitude": 77.17},
}

SENSORS = ["temperature", "humidity", "wind_speed", "pressure"]

SENSOR_UNITS = {
    "temperature": "C",
    "humidity": "%",
    "wind_speed": "km/h",
    "pressure": "hPa",
}

SOURCE_VARIABLES = {
    "temperature": "temperature_2m",
    "humidity": "relative_humidity_2m",
    "wind_speed": "wind_speed_10m",
    "pressure": "pressure_msl",
    "precipitation": "precipitation",
}

PHYSICAL_LIMITS = {
    "temperature": (-50.0, 60.0),
    "humidity": (0.0, 100.0),
    "wind_speed": (0.0, 250.0),
    "pressure": (870.0, 1085.0),
}

FAULT_TYPES = ["bias", "drift", "stuck", "spike", "precision", "dropout"]
EXTREME_TYPES = ["heat_wave", "cold_snap", "storm", "heavy_rain"]

FAULT_EPISODES_PER_TYPE = 10
EXTREME_EPISODES_PER_TYPE = 8

MAX_INTERPOLATION_GAP_HOURS = 2
REFERENCE_PERIOD_FRACTION = 0.30

FEATURE_COLUMNS = [
    "value_standardized",
    "deviation_from_median_24h",
    "rate_of_change",
    "rolling_mean_24h",
    "rolling_std_24h",
    "hour_of_day_sin",
    "hour_of_day_cos",
    "cross_sensor_deviation_score",
    "neighbour_deviation_score",
    "rule_violation_count",
]

CONSENSUS_VOTE_THRESHOLD = 2
CONSENSUS_VOTE_TOTAL = 5
REFERENCE_QUANTILE = 0.95

KMEANS_CLUSTERS = 6
DBSCAN_EPS = 1.4
DBSCAN_MIN_SAMPLES = 12
PCA_VARIANCE_TARGET = 0.90
ISOLATION_FOREST_TREES = 100
ISOLATION_FOREST_SUBSAMPLE = 256
LOF_NEIGHBOURS = 20

PRECISION_AT_K_VALUES = [10, 25, 50]

NEIGHBOUR_AGREEMENT_THRESHOLD = 0.35
SUSTAINED_EVENT_HOURS = 12

STATION_HEALTH_WINDOW_HOURS = 168
WATCH_ANOMALY_PERCENT = 5.0

DISCRETISATION_BINS = {
    "temperature": [-10.0, 15.0, 30.0, 45.0],
    "humidity": [0.0, 40.0, 70.0, 100.0],
    "wind_speed": [0.0, 12.0, 30.0, 250.0],
    "pressure": [870.0, 1000.0, 1015.0, 1085.0],
}

APRIORI_MIN_SUPPORT = 0.12
APRIORI_MIN_CONFIDENCE = 0.55

API_HOST = "127.0.0.1"
API_PORT = 8000
FRONTEND_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
