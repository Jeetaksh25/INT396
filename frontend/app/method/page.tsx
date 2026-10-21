import { getMetrics } from "@/lib/api";
import { MetricBlock, MetricsSummary } from "@/lib/types";

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function MetricRow({
  label,
  detector,
  baseline,
  higherIsBetter,
}: {
  label: string;
  detector: number;
  baseline: number;
  higherIsBetter: boolean;
}) {
  const detectorText = detector <= 1 ? percent(detector) : detector.toFixed(3);
  const baselineText = baseline <= 1 ? percent(baseline) : baseline.toFixed(3);
  const better = higherIsBetter ? detector >= baseline : detector <= baseline;

  return (
    <tr>
      <td>{label}</td>
      <td className="mono">{detectorText}</td>
      <td className="mono" style={{ color: "var(--ink-3)" }}>
        {baselineText}
      </td>
      <td className="mono" style={{ color: better ? "var(--ok)" : "var(--fault)" }}>
        {better ? "detector" : "baseline"}
      </td>
    </tr>
  );
}

function metricTable(metrics: MetricsSummary) {
  const detector: MetricBlock = metrics.detector;
  const baseline: MetricBlock = metrics.baseline_range_check;
  const topKeys = Object.keys(detector.precision_at_k);

  return (
    <>
      <MetricRow
        label="Fault detection rate"
        detector={detector.fault_detection_rate}
        baseline={baseline.fault_detection_rate}
        higherIsBetter
      />
      <MetricRow
        label="Fault classification rate"
        detector={detector.fault_classification_rate}
        baseline={baseline.fault_classification_rate}
        higherIsBetter
      />
      <MetricRow
        label="Extreme false-flag rate"
        detector={detector.extreme_false_flag_rate}
        baseline={baseline.extreme_false_flag_rate}
        higherIsBetter={false}
      />
      {topKeys.map((key) => (
        <MetricRow
          key={key}
          label={`Precision @ ${key}`}
          detector={detector.precision_at_k[key]}
          baseline={baseline.precision_at_k[key] ?? 0}
          higherIsBetter
        />
      ))}
      <MetricRow label="Precision (fault class)" detector={detector.precision} baseline={baseline.precision} higherIsBetter />
      <MetricRow label="Recall (fault class)" detector={detector.recall} baseline={baseline.recall} higherIsBetter />
      <MetricRow label="F1 (fault class)" detector={detector.f1} baseline={baseline.f1} higherIsBetter />
      <MetricRow
        label="False positives on clean data"
        detector={detector.false_positive_rate_clean}
        baseline={baseline.false_positive_rate_clean}
        higherIsBetter={false}
      />
    </>
  );
}

export default async function MethodPage() {
  let metrics: MetricsSummary | null = null;
  let error: string | null = null;

  try {
    metrics = await getMetrics();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "unknown error";
  }

  if (error || !metrics) {
    return (
      <div className="error-panel" style={{ marginTop: "2rem" }}>
        <h2 className="error-title">Metrics unavailable</h2>
        <p className="code-line">{error}</p>
      </div>
    );
  }

  const faultTypes = Object.keys(metrics.per_fault_type_recall);

  return (
    <>
      <header className="page-head">
        <div>
          <h1 className="page-title">Method and measured results</h1>
          <p className="page-sub">
            Five unsupervised detectors vote on every reading; a threshold of two votes declares an
            anomaly. The consistency rule tree then labels each episode. The fixed range check is
            the mandatory baseline.
          </p>
        </div>
        <div className="stamp">
          <div>{metrics.label_counts.total_readings.toLocaleString()} readings</div>
          <div>seed {metrics.random_seed} · {metrics.rule_count} rules</div>
        </div>
      </header>

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">Detector versus baseline</h2>
          <span className="section-note">higher is better except where noted</span>
        </div>
        <div className="panel-flush scroll-x">
          <table className="table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Consensus + discriminator</th>
                <th>Range check</th>
                <th>Winner</th>
              </tr>
            </thead>
            <tbody>{metricTable(metrics)}</tbody>
          </table>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">Recall by fault type</h2>
          <span className="section-note">what each failure mode gives away</span>
        </div>
        <div className="grid-two">
          <div className="panel">
            {faultTypes.map((fault) => {
              const value = metrics.per_fault_type_recall[fault] ?? 0;
              const baselineValue = metrics.baseline_per_fault_type_recall[fault] ?? 0;
              return (
                <div key={fault} className="meter">
                  <div className="meter-head">
                    <span className="meter-name">{fault}</span>
                    <span className="mono">
                      {percent(value)} <span style={{ color: "var(--ink-3)" }}>vs {percent(baselineValue)}</span>
                    </span>
                  </div>
                  <div className="meter-track">
                    <div className="meter-fill" style={{ width: `${value * 100}%` }} />
                  </div>
                  <div className="meter-track">
                    <div
                      className="meter-fill"
                      data-tone="baseline"
                      style={{ width: `${baselineValue * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="panel">
            <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Detector diagnostics</h3>
            <div className="detail-grid" style={{ borderTop: "none" }}>
              <div className="detail-cell">
                <div className="detail-key">PCA components</div>
                <div className="detail-value mono">{metrics.diagnostics.pca_components}</div>
              </div>
              <div className="detail-cell">
                <div className="detail-key">DBSCAN noise</div>
                <div className="detail-value mono">{metrics.diagnostics.dbscan_noise_percent.toFixed(1)}%</div>
              </div>
              <div className="detail-cell">
                <div className="detail-key">LOF outliers</div>
                <div className="detail-value mono">{metrics.diagnostics.lof_outlier_percent.toFixed(1)}%</div>
              </div>
              <div className="detail-cell">
                <div className="detail-key">Reference rows</div>
                <div className="detail-value mono">{metrics.diagnostics.reference_rows.toLocaleString()}</div>
              </div>
            </div>
            <div className="detail-grid">
              <div className="detail-cell">
                <div className="detail-key">Fault episodes</div>
                <div className="detail-value mono">{metrics.event_metrics.fault_events}</div>
              </div>
              <div className="detail-cell">
                <div className="detail-key">Extreme episodes</div>
                <div className="detail-value mono">{metrics.event_metrics.extreme_events}</div>
              </div>
              <div className="detail-cell">
                <div className="detail-key">Event precision (fault)</div>
                <div className="detail-value mono">{percent(metrics.event_metrics.fault_event_precision)}</div>
              </div>
              <div className="detail-cell">
                <div className="detail-key">Event precision (extreme)</div>
                <div className="detail-value mono">{percent(metrics.event_metrics.extreme_event_precision)}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">How a reading is judged</h2>
        </div>
        <ol className="note-list">
          <li>Features are standardised using the first 30% of the timeline, so the detector never learns from labels.</li>
          <li>k-Means distance, DBSCAN noise, PCA reconstruction error, Isolation Forest path length and LOF density each produce one vote against a reference-period quantile.</li>
          <li>Two or more votes mark an anomaly; consecutive flagged hours form an episode.</li>
          <li>Physical violation or an isolated single sensor with no neighbouring agreement → FAULT.</li>
          <li>Regional agreement plus multi-sensor coherence, or a sustained stable regime → EXTREME.</li>
          <li>Everything else falls back to FAULT with the reason <span className="mono">isolated_or_erratic</span>.</li>
        </ol>
      </section>
    </>
  );
}
