import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

plt.rcParams.update(
    {
        "figure.dpi": 140,
        "font.size": 9,
        "axes.edgecolor": "#5b6472",
        "axes.labelcolor": "#29313d",
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "xtick.color": "#5b6472",
        "ytick.color": "#5b6472",
        "axes.grid": True,
        "grid.color": "#d9dee6",
        "grid.linewidth": 0.6,
        "figure.facecolor": "white",
    }
)


def save_figure(figure, name):
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    target = config.FIGURES_DIR / name
    figure.tight_layout()
    figure.savefig(target, bbox_inches="tight")
    plt.close(figure)
    return target


def plot_sensor_distributions(dataset):
    figure, axes = plt.subplots(2, 2, figsize=(9, 6))
    for axis, sensor_name in zip(axes.ravel(), config.SENSORS):
        values = dataset[dataset["sensor_name"] == sensor_name]["clean_value"].dropna()
        axis.hist(values, bins=60, color="#3f5b8b", alpha=0.85)
        axis.set_title(f"{sensor_name} ({config.SENSOR_UNITS[sensor_name]})")
        axis.set_ylabel("readings")
    figure.suptitle("Clean reading distributions across all stations, 2023")
    return save_figure(figure, "01_sensor_distributions.png")


def plot_seasonal_cycle(dataset):
    frame = dataset.copy()
    frame["hour"] = pd.to_datetime(frame["timestamp"]).dt.hour
    frame["month"] = pd.to_datetime(frame["timestamp"]).dt.month
    figure, axes = plt.subplots(1, 2, figsize=(10, 3.8))

    temperature = frame[frame["sensor_name"] == "temperature"]
    diurnal = temperature.groupby("hour")["clean_value"].mean()
    axes[0].plot(diurnal.index, diurnal.values, color="#b4552d", linewidth=1.8)
    axes[0].set_title("Mean temperature by hour of day")
    axes[0].set_xlabel("hour (UTC)")
    axes[0].set_ylabel("°C")

    monthly = temperature.groupby("month")["clean_value"].mean()
    axes[1].bar(monthly.index, monthly.values, color="#3f5b8b")
    axes[1].set_title("Mean temperature by month")
    axes[1].set_xlabel("month")
    axes[1].set_ylabel("°C")
    return save_figure(figure, "02_seasonal_cycle.png")


def plot_station_correlation(clean_wide):
    temperatures = clean_wide.pivot(index="timestamp", columns="station_id", values="temperature")
    correlation = temperatures.corr()
    figure, axis = plt.subplots(figsize=(6.4, 5.2))
    image = axis.imshow(correlation, cmap="RdBu_r", vmin=-1, vmax=1)
    axis.set_xticks(range(len(correlation.columns)))
    axis.set_xticklabels(correlation.columns)
    axis.set_yticks(range(len(correlation.index)))
    axis.set_yticklabels(correlation.index)
    for row in range(len(correlation)):
        for column in range(len(correlation)):
            axis.text(
                column,
                row,
                f"{correlation.iloc[row, column]:.2f}",
                ha="center",
                va="center",
                fontsize=7,
                color="#20303f",
            )
    axis.set_title("Temperature correlation between stations")
    figure.colorbar(image, ax=axis, shrink=0.8)
    return save_figure(figure, "03_station_correlation.png")


def plot_fault_example(dataset):
    stuck_rows = dataset[dataset["fault_type"] == "stuck"]
    if stuck_rows.empty:
        return None
    sample = stuck_rows.iloc[0]
    station_id = sample["station_id"]
    sensor_name = sample["sensor_name"]
    series = dataset[
        (dataset["station_id"] == station_id) & (dataset["sensor_name"] == sensor_name)
    ].copy()
    series["timestamp"] = pd.to_datetime(series["timestamp"])
    window = series[
        (series["timestamp"] >= pd.Timestamp(sample["timestamp"]) - pd.Timedelta(hours=72))
        & (series["timestamp"] <= pd.Timestamp(sample["timestamp"]) + pd.Timedelta(hours=72))
    ]

    figure, axis = plt.subplots(figsize=(9, 3.6))
    axis.plot(window["timestamp"], window["clean_value"], color="#3f5b8b", label="clean", linewidth=1.3)
    axis.plot(
        window["timestamp"],
        window["measured_value"],
        color="#b4552d",
        label="injected",
        linewidth=1.1,
    )
    axis.set_title(f"Stuck sensor example — {station_id} {sensor_name}")
    axis.set_ylabel(config.SENSOR_UNITS[sensor_name])
    axis.legend(frameon=False, ncol=2)
    return save_figure(figure, "04_stuck_fault_example.png")


def plot_extreme_example(dataset):
    heat = dataset[(dataset["extreme_type"] == "heat_wave") & (dataset["sensor_name"] == "temperature")]
    if heat.empty:
        return None
    sample = heat.iloc[len(heat) // 2]
    series = dataset[
        (dataset["station_id"] == sample["station_id"])
        & (dataset["sensor_name"] == "temperature")
    ].copy()
    series["timestamp"] = pd.to_datetime(series["timestamp"])
    window = series[
        (series["timestamp"] >= pd.Timestamp(sample["timestamp"]) - pd.Timedelta(hours=96))
        & (series["timestamp"] <= pd.Timestamp(sample["timestamp"]) + pd.Timedelta(hours=96))
    ]
    humidity = dataset[
        (dataset["station_id"] == sample["station_id"]) & (dataset["sensor_name"] == "humidity")
    ].copy()
    humidity["timestamp"] = pd.to_datetime(humidity["timestamp"])
    humidity_window = humidity[
        (humidity["timestamp"] >= window["timestamp"].min())
        & (humidity["timestamp"] <= window["timestamp"].max())
    ]

    figure, axis = plt.subplots(figsize=(9, 3.8))
    axis.plot(window["timestamp"], window["measured_value"], color="#b4552d", label="temperature")
    axis.set_ylabel("°C")
    secondary = axis.twinx()
    secondary.plot(
        humidity_window["timestamp"],
        humidity_window["measured_value"],
        color="#3f7f6b",
        label="humidity",
        linewidth=1.1,
    )
    secondary.set_ylabel("%")
    secondary.grid(False)
    axis.set_title(f"Heat wave example — {sample['station_id']}, sensors move together")
    lines = axis.get_lines() + secondary.get_lines()
    axis.legend(lines, [line.get_label() for line in lines], frameon=False, loc="upper left")
    return save_figure(figure, "05_heat_wave_example.png")


def plot_confusion(metrics):
    confusion = metrics["confusion"]
    categories = ["fault", "extreme", "clean"]
    flagged = [confusion["fault_flagged"], confusion["extreme_flagged"], confusion["clean_flagged"]]
    totals = [confusion["fault_total"], confusion["extreme_total"], confusion["clean_total"]]
    rates = [flagged[index] / max(totals[index], 1) for index in range(3)]

    figure, axis = plt.subplots(figsize=(6.4, 3.4))
    bars = axis.bar(categories, rates, color=["#b4552d", "#3f6fa8", "#7d8794"])
    for bar, rate, total in zip(bars, rates, totals):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{rate * 100:.1f}%\n(n={total})",
            ha="center",
            fontsize=8,
        )
    axis.set_ylim(0, max(rates) * 1.35 + 0.02)
    axis.set_ylabel("share flagged as anomaly")
    axis.set_title("Flag rate by ground-truth class")
    return save_figure(figure, "06_flag_rates.png")


def plot_fault_type_recall(metrics):
    fault_types = list(metrics["per_fault_type_recall"])
    detector = [metrics["per_fault_type_recall"][name] for name in fault_types]
    baseline = [metrics["baseline_per_fault_type_recall"][name] for name in fault_types]
    positions = np.arange(len(fault_types))

    figure, axis = plt.subplots(figsize=(8, 3.6))
    axis.bar(positions - 0.2, detector, width=0.4, label="consensus", color="#b4552d")
    axis.bar(positions + 0.2, baseline, width=0.4, label="range check", color="#9aa4b2")
    axis.set_xticks(positions)
    axis.set_xticklabels(fault_types)
    axis.set_ylabel("recall")
    axis.set_ylim(0, 1.05)
    axis.legend(frameon=False)
    axis.set_title("Per-fault-type recall: consensus versus range check")
    return save_figure(figure, "07_fault_type_recall.png")


def plot_detection_timeline(detections):
    frame = detections.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame["day"] = frame["timestamp"].dt.floor("D")
    daily = frame.groupby("day").agg(
        faults=("is_fault_flagged", "sum"),
        extremes=("is_extreme_flagged", "sum"),
        anomalies=("is_anomaly", "sum"),
    )

    figure, axis = plt.subplots(figsize=(10, 3.4))
    axis.plot(daily.index, daily["anomalies"], color="#6b7684", linewidth=0.9, label="all anomalies")
    axis.plot(daily.index, daily["faults"], color="#b4552d", linewidth=1.2, label="classified fault")
    axis.plot(daily.index, daily["extremes"], color="#3f6fa8", linewidth=1.2, label="classified extreme")
    axis.set_ylabel("flagged readings per day")
    axis.legend(frameon=False, ncol=3)
    axis.set_title("Daily detections across the network, 2023")
    return save_figure(figure, "08_detection_timeline.png")


def plot_vote_histogram(detections):
    figure, axis = plt.subplots(figsize=(6.4, 3.2))
    counts = detections["vote_count"].value_counts().sort_index()
    axis.bar(counts.index, counts.values, color="#3f5b8b")
    axis.set_xlabel("consensus votes (of 5)")
    axis.set_ylabel("readings")
    axis.set_yscale("log")
    axis.set_title("How many models agree before a reading is flagged")
    return save_figure(figure, "09_vote_distribution.png")


def build_all_figures():
    dataset = pd.read_parquet(config.DATASET_PARQUET)
    clean_wide = pd.read_parquet(config.PROCESSED_DIR / "clean_wide.parquet")
    detections = pd.read_csv(config.DETECTIONS_CSV, parse_dates=["timestamp"])
    with open(config.METRICS_JSON, "r", encoding="utf-8") as handle:
        metrics = json.load(handle)

    outputs = [
        plot_sensor_distributions(dataset),
        plot_seasonal_cycle(dataset),
        plot_station_correlation(clean_wide),
        plot_fault_example(dataset),
        plot_extreme_example(dataset),
        plot_confusion(metrics),
        plot_fault_type_recall(metrics),
        plot_detection_timeline(detections),
        plot_vote_histogram(detections),
    ]
    return [str(path) for path in outputs if path is not None]


if __name__ == "__main__":
    for figure_path in build_all_figures():
        print(figure_path)
