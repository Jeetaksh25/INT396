# Methodology

## Problem

Given hourly readings $x_{s,t}^{(m)}$ for station $s$, hour $t$ and sensor $m \in$
{temperature, humidity, wind_speed, pressure}, and **no labels**, decide which readings are anomalous,
then decide for each anomaly whether the instrument is failing (FAULT) or the weather is genuinely
extreme (EXTREME).

The distinction is the whole project. A faulty thermometer produces weather that could never happen;
a heat wave produces weather that is extreme but physically coherent.

## No labels used at fit time

Ground-truth columns (`is_fault_injected`, `fault_type`, `is_extreme_event`, `extreme_type`) are written
by the simulation layer and are used **only** by `src/evaluation/metrics.py`. Three mechanisms keep it
that way:

1. `src/evaluation/run_experiment.py` drops them at load via `strip_label_columns()` before any feature
   code runs.
2. `src/features/leakage_guard.py` raises if a label column ever reaches a feature frame, the detector
   input, the detector output, or the reference frame.
3. Unit tests assert the guard fires on a labelled frame.

No clustering, reconstruction, density or tree model in `src/algorithms/` imports or reads a label.

## Data

Real hourly ERA5 reanalysis for eight Indian stations across 2023 (see `data_sources.md`).
280,320 tidy readings. The first 30% of the timeline (84,096 readings) forms the **reference period**,
used for scaling, vote thresholds and the median model.

## Fault injection

Six physically-motivated failure modes, applied to a single sensor of a single station per episode,
10 episodes each:

| Fault | Mechanism | Magnitude | Duration |
|---|---|---|---|
| bias | constant offset | 3–8 σ | 12–72 h |
| drift | linear ramp | 2–5 σ | 3–10 days |
| stuck | frozen value | — | 6–48 h |
| spike | isolated jumps | 5–12 σ | single samples |
| precision | quantisation + noise | q ∈ {1,2,5} | 24–120 h |
| dropout | missing values | 10–40% of window | 3–24 h |

Total injected coverage: 5,044 readings (1.80%). Every episode touches exactly one sensor, which is
what makes "the other sensors are fine" informative later.

## Extreme-event injection

Four coherent events, applied to **all** sensors of a station with a raised-cosine profile so the ramp
looks natural:

| Event | Effect | Duration |
|---|---|---|
| heat_wave | +6–12 °C, humidity −10–25%, pressure slightly down | 3–7 days |
| cold_snap | −6–15 °C, wind up | 2–5 days |
| storm | wind ×2–4, pressure −8–20 hPa | 12–36 h |
| heavy_rain | humidity → 90–100%, temperature −2–6 °C | 6–24 h |

Events are injected only in their plausible season and clipped to physical bounds. With probability 0.5
the same event is applied to a second station at the same time, which is what makes neighbour agreement
a usable signal. Total coverage: 12,060 readings (4.30%).

## Features

Per `(station, sensor, timestamp)`, eleven features — all computed from `measured_value` only:

| Feature | Definition | Targets |
|---|---|---|
| value_standardized | (x − μ_ref)/σ_ref | all |
| deviation_from_median_24h | x − median₂₄ | bias, drift |
| rate_of_change | xₜ − xₜ₋₁ | spike |
| rolling_mean_24h | trailing mean | drift |
| rolling_std_24h | trailing std | stuck (→0) |
| flatline_score | 1 when a run of ~6 hours is unchanged to 2dp | stuck |
| hour_of_day_sin, cos | cyclic encoding | removes diurnal normal variation |
| rule_violation_count | strong association rules broken | physics plausibility |
| physics_violation_count | dew point > temperature, humidity outside [0,100], pressure outside [870,1085] | impossible readings |
| missing_reading | x is NaN | dropout |

Standardisation uses reference-period mean and standard deviation, computed **per station** (Delhi and
Shimla differ by 15 °C; a shared scale would bury one of them). The same reference window sets every
vote threshold.

## Consensus detector

Five unsupervised models, each producing one score per reading:

| Model | Score | Syllabus unit |
|---|---|---|
| k-Means (k=6, k-Means++) | distance to assigned centroid | II |
| DBSCAN (eps=1.4, min_samples=12) | 1 if noise, else 0 | III |
| PCA (components for 90% variance) | reconstruction error | IV |
| Isolation Forest (100 trees, 256 subsample) | 2^(−E[h]/c(n)) | V |
| LOF (20 neighbours) | −LOF | V |

Each score is converted to a binary vote by comparing against its own **reference-period quantile**
(0.99). Votes are summed; three or more votes out of five marks the reading anomalous
(`is_anomaly`). The soft score `vote_count / 5` drives precision@K ranking.

The threshold was tuned on the reference period only. Two votes raised fault recall from 0.393 to
0.600 but pushed F1 below the range-check baseline, so three is the operating point.

The reference quantile is deliberately conservative: a threshold at the 95th percentile of the
reference period flags 5% of healthy data by construction, which is what a naive per-model threshold
would do.

## Fault-vs-extreme discriminator

Consecutive anomalous hours for the same station and sensor form an episode. Each episode gets one
label from a transparent rule tree using three consistency signals:

- **anomalous_sensor_count** — how many of the four sensors at that station-hour are flagged.
- **neighbour_agreement** — mean share of the other seven stations whose same sensor deviates by more
  than 1.5 σ in the same hour.
- **physics_violation** — whether any hard physical rule is violated in the episode.

```
if physics_violation:                                      -> FAULT   (physics_inconsistent)
elif single_sensor_anomaly and no neighbour agreement:      -> FAULT   (isolated_sensor)
elif neighbour agreement and multiple sensors flagged:      -> EXTREME (regional_coherent)
elif duration > 12h and neighbour agreement:                -> EXTREME (sustained_regime)
else:                                                      -> FAULT   (isolated_or_erratic)
```

The reasoning: a genuine heat wave moves temperature and humidity together and hits neighbouring
stations; a broken thermometer deviates alone and does not spread.

## Baseline

Fixed physical limits applied row-wise, no learning:

| Sensor | Min | Max |
|---|---|---|
| temperature | −5 | 45 |
| humidity | 0 | 100 |
| wind_speed | 0 | 120 |
| pressure | 950 | 1050 |

Anything outside, or NaN, is flagged as FAULT. This is the naive quality-control rule every network
already runs, and it is the reference for every table.

## Station health

Per station over the trailing 168 hours:

```
FAULT           if any fault-labelled event
EXTREME_EVENT   elif any extreme-labelled event
WATCH           elif anomalous share > 5%
HEALTHY         otherwise
```
