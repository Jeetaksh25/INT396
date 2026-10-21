# Experiment Log

Every entry records date, configuration, the numbers actually produced, and what they mean.
Numbers are copied from `backend/results/metrics_summary.json` and the tuning harness output.

## Environment

| Item | Value |
|---|---|
| Python | 3.10.10 |
| numpy / pandas | 2.2.6 / 2.3.3 |
| Node | 24.20.0 |
| Random seed | 42 (data simulation), 42+1 (fault injection) |
| Reference period | first 30% of the timeline (84,096 readings) |
| Total readings | 280,320 |

## Run 1 — first complete pipeline

Configuration: reference quantile 0.95, vote threshold 2 of 5, station-shared feature scaling.

| Metric | Detector | Baseline |
|---|---|---|
| Fault detection rate | 0.5613 | 0.2768 |
| Fault classification rate | 0.5147 | 0.2768 |
| Extreme false-flag rate | 0.1404 | 0.0037 |
| Precision (fault) | 0.0855 | 1.0000 |
| F1 | 0.1484 | 0.4335 |
| FPR on clean | 0.1059 | 0.0000 |
| P@10 / 25 / 50 | 0.00 / 0.32 / 0.54 | 1.00 / 1.00 / 1.00 |

Observations: high recall but 10.6% of clean data flagged — the detector was firing constantly, so
precision collapsed. Root cause: the cross-sensor and neighbour features were computed per station-hour
and copied onto all four sensors, so all four sensors of a station always received the same score and
were always flagged together. That destroyed the very signal the discriminator needed, and it inflated
the clean alarm rate. The discriminator also took 913 s because it looped over 7,706 events in Python.

## Run 2 — sensor-local features

Changes: removed the station-shared cross-sensor and neighbour columns from the feature matrix (they
belong to the discriminator, not the detector); reference quantile tightened to 0.99; discriminator
rewritten to vectorize context building and grouping.

| Metric | Detector | Baseline |
|---|---|---|
| Fault detection rate | 0.2657 | 0.2768 |
| Fault classification rate | 0.0028 | 0.2768 |
| Extreme false-flag rate | 0.0182 | 0.0037 |
| Precision (fault) | 0.5419 | 1.0000 |
| F1 | 0.3565 | 0.4335 |
| FPR on clean | 0.0040 | 0.0000 |
| P@10 / 25 / 50 | 0.60 / 0.72 / 0.80 | 1.00 / 1.00 / 1.00 |

Observations: clean false positives fell from 10.6% to 0.4% and precision rose from 0.086 to 0.54.
Per-fault recall exposed three genuine bugs:

- `dropout` recall 0.000 — the injector marked a whole window as faulty but only set a few values to
  NaN, so most labelled rows still held a valid reading.
- `stuck` recall 0.000 — a frozen value is statistically normal, and no feature described flatlining.
- `drift` recall 0.063 — a slow ramp stays inside normal ranges.

Also: LOF scores were returned negated, so the most anomalous points had the *lowest* score and LOF
voted almost backwards.

Runtime: detector 100 s, discriminator 1.2 s (down from 913 s).

## Run 3 — bug fixes

Changes: LOF sign corrected; dropout mask narrowed to the actually-missing rows; `flatline_score`
feature added (six consecutive identical readings); neighbour agreement now measured against a 4σ
deviation threshold instead of 1.5σ.

| Metric | Detector | Baseline |
|---|---|---|
| Fault detection rate | 0.3933 | 0.2811 |
| F1 | 0.4514 | 0.4389 |
| Precision (fault) | 0.5296 | 1.0000 |
| FPR on clean | 0.0056 | 0.0000 |
| P@10 / 25 / 50 | 1.00 / 1.00 / 0.96 | 1.00 / 1.00 / 1.00 |

Per-fault recall:

| Fault | Detector | Baseline |
|---|---|---|
| bias | 0.5119 | see below |
| drift | 0.1137 | |
| stuck | 0.8057 | |
| spike | 0.6253 | |
| precision | 0.0414 | |
| dropout | 1.0000 | |

Observations: dropout and stuck are now detected, the top-50 ranking is essentially perfect, and the
detector finally beats the baseline on F1 (0.451 vs 0.439). But `fault_classification_rate` is 0.003 —
the discriminator labels nearly every episode EXTREME. Root cause: "multiple sensors flagged at this
station-hour" was read from the consensus flags, which are station-hour level for all four sensors, so
coherence was always true.

## Metric interpretation notes

- FDR compares "any anomaly flag" against "any flag at all", so both methods are scored on the same
  footing. The baseline's FDR (0.28) is high only because bias and spike faults push values outside its
  fixed limits; it cannot see drift, stuck, precision loss or dropout.
- P@K for the baseline is degenerate: it has no graded score, so its flags are ordered arbitrarily and
  it cannot rank. That is precisely the operational gap the consensus score fills.
- Extreme false-flag rate is computed on readings, so a single 7-day heat wave contributes ~168 readings
  and dominates the average. Event-level precision is reported alongside it for that reason.
