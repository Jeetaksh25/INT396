# Method and measured results

Numbers below come from `backend/results/metrics_summary.json` produced by
`python -m src.evaluation.run_experiment` with `config.RANDOM_SEED = 42`.

## Headline table

| Metric | Consensus + discriminator | Fixed range check | Winner |
|---|---|---|---|
| Fault detection rate | 0.3933 | 0.2811 | detector (+0.11) |
| Fault classification rate | 0.2741 | 0.2811 | baseline |
| Extreme false-flag rate | 0.0085 | 0.0037 | baseline |
| Precision (fault class) | 0.5296 | 1.0000 | baseline |
| Recall (fault class) | 0.3933 | 0.2811 | detector |
| F1 (fault class) | 0.4514 | 0.4389 | detector |
| False positives on clean data | 0.0056 | 0.0000 | baseline |
| Precision @ 10 | 1.0000 | 1.0000 | tie |
| Precision @ 25 | 1.0000 | 1.0000 | tie |
| Precision @ 50 | 0.9600 | 1.0000 | baseline |

Read this honestly. The detector wins on **fault detection rate, recall and F1** and matches the
baseline at the very top of the ranking. It loses on clean-data false positives (0.56% versus 0%)
and on extreme false-flag rate (0.85% versus 0.37%). Those two losses are small in absolute terms
but they are real, and the report should state them.

The precision@K numbers need context: the baseline has no graded anomaly score, so its flags are
ordered arbitrarily. It "wins" P@50 only because it flags so few readings that almost everything it
flags is a true fault. The consensus score is what an operator could actually rank by.

## Per-fault-type recall

| Fault | Detector | What it means |
|---|---|---|
| bias | 0.5119 | half of constant offsets move far enough to be flagged |
| drift | 0.1137 | slow ramps stay inside normal ranges — the hard case |
| stuck | 0.8057 | the flatline feature catches frozen sensors reliably |
| spike | 0.6253 | isolated jumps are flagged, though some land inside limits |
| precision | 0.0414 | quantisation noise is nearly invisible to these models |
| dropout | 1.0000 | a missing reading is unambiguous |

The three wins that matter: dropout and stuck are invisible to a range check by construction and the
detector catches them almost perfectly. Drift and precision degradation remain weaknesses and are
stated as such in the limitations.

## Extreme-event handling

Extreme false-flag rate of 0.85% means that of 12,060 extreme readings, 103 were labelled FAULT. The
discriminator correctly identified the rest either as anomalies with an EXTREME verdict or did not
flag them at all.

The mechanism that produced this: extremes move several sensors of the same station together
(other-sensor deviation 0.495 on average) while injected faults usually move only one
(other-sensor deviation 0.241). The rule tree uses that coherence ratio, plus neighbour agreement and
a physics check.

## Event-level results

| Quantity | Value |
|---|---|
| Episodes grouped | 1,203 |
| Fault-labelled episodes | majority |
| Extreme-labelled episodes | small minority |
| Median episode length (fault) | 1 hour |
| Median episode length (extreme) | 2 hours |

Episode fragmentation is a known weakness: because the vote threshold is strict, a long event often
produces several short episodes instead of one long one. Merging with a 6-hour gap tolerance helps but
does not fully solve it.

## Detector diagnostics

| Item | Value |
|---|---|
| PCA components for 90% variance | 10 |
| DBSCAN noise share | 22.6% |
| LOF outlier share | 7.3% |
| Reference rows | 84,096 |
| Total readings | 280,320 |
| Association rules mined | 14 |
| Detector runtime | ~100 s |
| Discriminator runtime | ~2 s |

## Ablation notes

Removing the consensus and using a single model was not run as a formal ablation, but the per-model
scores recorded in `results/detections.csv` allow it: each of the five columns
(`kmeans_score`, `dbscan_score`, `pca_score`, `isolation_score`, `lof_score`) can be thresholded
independently. The consensus exists because the models disagree in useful ways — DBSCAN flags 22.6%
of readings as noise on its own, which alone would be unusable.

## Honest limitations

1. Faults and extremes are synthetic. Real failure logs are not public, so magnitudes are authored and
   the numbers are therefore optimistic relative to a real deployment.
2. ERA5 is already quality-controlled; injecting faults into clean data is the standard workaround, not
   a substitute for real failure data.
3. The rule tree encodes meteorological reasoning. A new fault type that happens to move several
   sensors coherently would be misclassified as an extreme.
4. Episode fragmentation means the event table over-reports the number of distinct incidents.
5. `precision` on the fault class is 0.53, not 0.9. The detector flags roughly twice as many readings
   as there are true faults. That is the correct trade for a monitoring alarm, but it must be stated.
