# Metrics Definitions

Every number on the dashboard is defined here with its formula and the file that computes it.

## Required metrics

### Fault detection rate (FDR)

```
FDR = |{fault readings flagged anomalous}| / |{fault readings}|
```

Recall on injected faults, ignoring the fault/extreme verdict. Proves the detector *notices* a failing
instrument at all.
Computed by `src/evaluation/metrics.py::fault_detection_rate`.

### Fault classification rate (FCR)

```
FCR = |{fault readings labelled FAULT}| / |{fault readings}|
```

The stricter version: the reading was flagged **and** the discriminator called it a fault rather than
an extreme. This is the number that matters operationally, because a fault labelled EXTREME is a fault
that never gets repaired.
Computed by `fault_classification_rate`.

### Extreme false-flag rate (EFFR)

```
EFFR = |{extreme readings labelled FAULT}| / |{extreme readings}|
```

The penalty metric. A genuine heat wave wrongly called a broken thermometer means an operator silences a
real event. Lower is better, and this is where the baseline loses badly.
Computed by `extreme_false_flag_rate`.

### Precision at K

```
P@K = |{true anomalies among the K highest anomaly_score readings}| / K
```

Ranking quality for an operator who only inspects the top K. "True anomaly" means fault **or** extreme.
Reported for K ∈ {10, 25, 50} from `config.PRECISION_AT_K_VALUES`.
Computed by `precision_at_k`.

## Supporting metrics

| Metric | Formula | What it proves |
|---|---|---|
| Precision | TP / (TP + FP) on the fault class | how many flags are real faults |
| Recall | TP / (TP + FN) on the fault class | same as FDR |
| F1 | 2PR / (P + R) | single-number fault accuracy |
| False-positive rate on clean data | flagged clean / clean total | quiet-season alarm rate |
| Per-fault-type recall | flagged / total per fault type | which failure modes each method misses |
| Per-station FDR | as FDR, per station | whether geography biases the detector |
| Event precision | correctly labelled episodes / episodes | quality of the grouping + rule tree |

## Confusion output

`metrics_summary.json` also stores raw counts, not just ratios:

```json
"confusion": {
  "fault_flagged": 0, "fault_total": 0,
  "extreme_flagged": 0, "extreme_total": 0,
  "clean_flagged": 0, "clean_total": 0
}
```

Ratios alone hide sample size; the report quotes both.

## Baseline parity

Every metric block is computed twice with identical code — once with the consensus flags and once with
the range-check flags — so the comparison cannot drift. The baseline is given a score of
`baseline_flag` for ranking purposes, which is why its P@K reflects "flag first, everything else
unordered".

## What each metric cannot tell you

- FDR says nothing about *when* a fault was caught; a detector that only fires at the end of a 10-day
  drift still scores.
- EFFR is computed on readings, so one long extreme event contributes thousands of rows and dominates
  the number. Event precision exists to counter that.
- P@K with K=10 over 280,320 readings is a stress test of ranking extremeness, not a realistic
  inspection budget.
