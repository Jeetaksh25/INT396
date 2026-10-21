import numpy as np
import pandas as pd

import config


def load_raw():
    dataset = pd.read_parquet(config.DATASET_PARQUET)
    dataset["timestamp"] = pd.to_datetime(dataset["timestamp"])
    wide = (
        dataset.pivot_table(
            index=["station_id", "timestamp"],
            columns="sensor_name",
            values="measured_value",
            aggfunc="first",
        )
        .sort_index()
        .reindex(columns=config.SENSORS)
    )
    label_frame = (
        dataset.groupby(["station_id", "timestamp"])
        .agg(
            fault=("is_fault_injected", "max"),
            extreme=("is_extreme_event", "max"),
        )
        .sort_index()
    )
    return dataset, wide, label_frame


def climatology_deviation(wide):
    index = wide.index
    keys = pd.DataFrame(
        {
            "month": index.get_level_values("timestamp").month,
            "hour": index.get_level_values("timestamp").hour,
        },
        index=index,
    )
    reference_rows = index.get_level_values("timestamp") <= (
        index.get_level_values("timestamp").min()
        + (index.get_level_values("timestamp").max() - index.get_level_values("timestamp").min())
        * config.REFERENCE_PERIOD_FRACTION
    )

    centre = wide[reference_rows].groupby([keys[reference_rows].month, keys[reference_rows].hour]).median()
    spread = (
        wide[reference_rows]
        .groupby([keys[reference_rows].month, keys[reference_rows].hour])
        .quantile(0.75)
        - wide[reference_rows]
        .groupby([keys[reference_rows].month, keys[reference_rows].hour])
        .quantile(0.25)
    ).replace(0.0, np.nan)
    centre = centre.reindex(keys.set_index(["month", "hour"]).index)
    spread = spread.reindex(keys.set_index(["month", "hour"]).index)
    centre.index = index
    spread.index = index
    deviation = (wide - centre).abs() / spread
    return deviation.fillna(0.0)


def label_episodes(label_frame):
    truth = pd.Series("clean", index=label_frame.index)
    truth[label_frame["extreme"] == 1] = "EXTREME"
    truth[label_frame["fault"] == 1] = "FAULT"
    return truth


def summarise(deviation, truth, threshold, neighbour_count):
    sensor_names = list(deviation.columns)
    rows = []
    for sensor_name in sensor_names:
        other_names = [name for name in sensor_names if name != sensor_name]
        other_flags = (deviation[other_names] > threshold).sum(axis=1)
        own_flag = deviation[sensor_name] > threshold
        rows.append(
            pd.DataFrame(
                {
                    "truth": truth,
                    "own": own_flag.astype(int),
                    "others": other_flags,
                }
            )
        )
    stacked = pd.concat(rows)
    result = {}
    for name in ["clean", "FAULT", "EXTREME"]:
        subset = stacked[stacked["truth"] == name]
        result[name] = {
            "rows": int(len(subset)),
            "own_rate": round(float(subset["own"].mean()), 4),
            "others_mean": round(float(subset["others"].mean()), 3),
            "coherent_rate": round(float((subset["others"] >= neighbour_count).mean()), 4),
            "isolated_rate": round(
                float(((subset["own"] == 1) & (subset["others"] == 0)).mean()), 4
            ),
        }
    return result


def main():
    _, wide, label_frame = load_raw()
    deviation = climatology_deviation(wide)
    truth = label_episodes(label_frame)

    for threshold in [1.5, 2.0, 2.5, 3.0]:
        for neighbour_count in [1, 2, 3]:
            summary = summarise(deviation, truth, threshold, neighbour_count)
            print(
                f"threshold={threshold} neighbours>={neighbour_count} "
                f"clean={summary['clean']['coherent_rate']} "
                f"fault={summary['FAULT']['coherent_rate']} "
                f"extreme={summary['EXTREME']['coherent_rate']} "
                f"isolated_clean={summary['clean']['isolated_rate']} "
                f"isolated_fault={summary['FAULT']['isolated_rate']}"
            )

    print()
    for threshold in [2.0, 2.5, 3.0]:
        summary = summarise(deviation, truth, threshold, 2)
        print(f"--- threshold {threshold} ---")
        for name, values in summary.items():
            print(f"  {name}: {values}")


if __name__ == "__main__":
    main()
