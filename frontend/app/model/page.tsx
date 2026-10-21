import Link from "next/link";
import { ShieldCheck, ArrowUpRight } from "@phosphor-icons/react/dist/ssr";
import { getModelCard } from "@/lib/api";
import { ModelCard, ModelSpec } from "@/lib/types";
import { PageHead, Section, KvList, Callout, StepList, TickedNumber } from "@/components/page-parts";
import { TopBar } from "@/components/top-bar";
import { RecallBars, FlagRateBars } from "@/components/charts";
import { BlurFade } from "@/components/ui/blur-fade";

const percent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;

const formatParam = (value: unknown) => {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }
  if (typeof value === "boolean") {
    return value ? "enabled" : "disabled";
  }
  return String(value);
};

function ModelTile({ model, index }: { model: ModelSpec; index: number }) {
  return (
    <BlurFade delay={index * 0.04} duration={0.32} offset={16}>
      <article className="model-card">
        <div className="model-head">
          <div>
            <h3 className="model-name">{model.name}</h3>
            <p className="model-family">
              {model.family} · {model.unit}
            </p>
          </div>
          <span className="chip" data-tone="accent">
            {percent(model.vote_rate, 2)} votes
          </span>
        </div>

        <div className="model-scores">
          <div className="model-score">
            <span className="model-score-key">Precision</span>
            <span className="model-score-value">{model.precision.toFixed(3)}</span>
          </div>
          <div className="model-score">
            <span className="model-score-key">Recall</span>
            <span className="model-score-value">{model.recall.toFixed(3)}</span>
          </div>
          <div className="model-score">
            <span className="model-score-key">F1</span>
            <span className="model-score-value">{model.f1.toFixed(3)}</span>
          </div>
        </div>

        <div>
          <p className="mono-label" style={{ marginBottom: "0.5rem" }}>
            Hyperparameters
          </p>
          <div className="params">
            {Object.entries(model.hyperparameters).map(([key, value]) => (
              <div className="param" key={key}>
                <span className="param-key">{key.replace(/_/g, " ")}</span>
                <span className="param-value">{formatParam(value)}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <p className="mono-label" style={{ marginBottom: "0.35rem" }}>
            Anomaly score
          </p>
          <p style={{ fontSize: "0.8125rem", color: "var(--ink-2)", lineHeight: 1.5 }}>
            {model.score}
          </p>
        </div>

        <p style={{ fontSize: "0.8125rem", color: "var(--ink-3)", lineHeight: 1.55 }}>
          {model.why}
        </p>

        <div className="def-list" style={{ marginTop: "auto" }}>
          <div className="def-row">
            <span className="def-key">Fault-only recall</span>
            <span className="def-value">{percent(model.fault_recall)}</span>
          </div>
          <div className="def-row">
            <span className="def-key">Score mean / p99</span>
            <span className="def-value">
              {model.score_mean.toFixed(2)} / {model.score_p99.toFixed(2)}
            </span>
          </div>
        </div>
      </article>
    </BlurFade>
  );
}

export default async function ModelPage() {
  let card: ModelCard;
  try {
    card = await getModelCard();
  } catch (caught) {
    const message = caught instanceof Error ? caught.message : "unknown error";
    return (
      <>
        <TopBar />
        <PageHead title="Model card" description="Model metadata could not be loaded." />
        <div className="error-panel">
          <h2 className="error-title">Model card unavailable</h2>
          <p className="code-line">{message}</p>
          <p className="code-line">python -m src.evaluation.model_card</p>
        </div>
      </>
    );
  }

  const dataset = card.dataset;
  const consensus = card.consensus;
  const bestModel = [...card.models].sort((a, b) => b.f1 - a.f1)[0];

  return (
    <>
      <TopBar />
      <PageHead
        size="large"
        title="The model, in full"
        description="Five classical unsupervised detectors, each implemented from the formulas with NumPy, combined by a two-of-five vote and read through a consistency rule tree. No training label is used anywhere in the model path."
        aside={
          <>
            <span className="chip" data-tone="accent">
              <ShieldCheck size={12} weight="bold" />
              unsupervised
            </span>
            <span>{card.models.length} detectors · {card.features.count} features</span>
            <span className="mono-label" style={{ letterSpacing: 0 }}>
              seed 42 · {card.runtime.detector_seconds ?? 0}s detector
            </span>
          </>
        }
      />

      <div className="metric-grid">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <div className="metric">
            <div className="metric-top">
              <span className="metric-label">Readings scored</span>
            </div>
            <div className="metric-value">
              <TickedNumber value={dataset.rows} />
            </div>
            <div className="metric-foot">
              <span>
                {dataset.reference_rows.toLocaleString()} in the reference window
              </span>
            </div>
          </div>
        </BlurFade>
        <BlurFade delay={0.06} duration={0.32} offset={14}>
          <div className="metric">
            <div className="metric-top">
              <span className="metric-label">Fault detection</span>
            </div>
            <div className="metric-value">
              <TickedNumber
                value={card.detector.fault_detection_rate * 100}
                decimals={1}
                suffix="%"
              />
            </div>
            <div className="metric-foot">
              <span className="chip" data-tone="up">
                +{(card.delta.fault_detection_rate * 100).toFixed(1)}pp
              </span>
              <span>over the range check</span>
            </div>
          </div>
        </BlurFade>
        <BlurFade delay={0.1} duration={0.32} offset={14}>
          <div className="metric">
            <div className="metric-top">
              <span className="metric-label">PCA components kept</span>
            </div>
            <div className="metric-value">
              <TickedNumber value={consensus.pca_components} />
            </div>
            <div className="metric-foot">
              <span>at 90% explained variance</span>
            </div>
          </div>
        </BlurFade>
        <BlurFade delay={0.14} duration={0.32} offset={14}>
          <div className="metric">
            <div className="metric-top">
              <span className="metric-label">Best single detector</span>
            </div>
            <div className="metric-value" style={{ fontSize: "1.65rem" }}>
              {bestModel.name}
            </div>
            <div className="metric-foot">
              <span>F1 {bestModel.f1.toFixed(3)} on its own</span>
            </div>
          </div>
        </BlurFade>
      </div>

      <Section
        title="Detectors"
        note="Precision, recall and F1 are measured against the injected ground truth, after thresholding each score at its own reference-period quantile."
      >
        <div className="model-grid">
          {card.models.map((model, index) => (
            <ModelTile key={model.key} model={model} index={index} />
          ))}
        </div>
      </Section>

      <Section
        title="Consensus behaviour"
        note={`A reading is an anomaly when at least ${consensus.vote_threshold} of ${consensus.vote_total} detectors vote. Most readings draw no votes at all, which is what makes a unanimous flag meaningful.`}
      >
        <div className="split">
          <BlurFade delay={0.02} duration={0.32} offset={16}>
            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">Vote distribution</h3>
                  <p className="card-caption">
                    share of readings by how many detectors agree
                  </p>
                </div>
                <span className="chip" data-tone="neutral">
                  threshold {consensus.vote_threshold} of {consensus.vote_total}
                </span>
              </div>
              <div style={{ padding: "0.5rem 1.25rem 1.25rem" }}>
                {Object.entries(consensus.agreement_share).map(([votes, share]) => {
                  const flagged = Number(votes) >= consensus.vote_threshold;
                  const count = consensus.agreement_counts[votes] ?? 0;
                  const peak = Math.max(...Object.values(consensus.agreement_share));
                  const width = Math.sqrt(share / peak) * 100;
                  return (
                    <div className="meter" key={votes}>
                      <div className="meter-head">
                        <span className="meter-name">
                          {votes} {Number(votes) === 1 ? "vote" : "votes"}
                          <span
                            className="chip"
                            data-tone={flagged ? "accent" : "neutral"}
                          >
                            {flagged ? "anomaly" : "normal"}
                          </span>
                        </span>
                        <span className="meter-value">
                          <span className="meter-count">{count.toLocaleString()}</span>
                          <span>{share > 0 && share < 0.001 ? "<0.1%" : percent(share, 2)}</span>
                        </span>
                      </div>
                      <div className="meter-track">
                        <div
                          className="meter-fill"
                          data-tone={flagged ? undefined : "baseline"}
                          style={{ width: `${width}%`, height: "100%" }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </BlurFade>

          <BlurFade delay={0.06} duration={0.32} offset={16}>
            <div className="card card-pad">
              <h3 className="card-title" style={{ marginBottom: "0.75rem" }}>
                Aggregation settings
              </h3>
              <KvList
                rows={[
                  { key: "Vote rule", value: `≥ ${consensus.vote_threshold} of ${consensus.vote_total}` },
                  {
                    key: "Vote quantile",
                    value: `${(consensus.reference_quantile * 100).toFixed(0)}th percentile`,
                  },
                  {
                    key: "Unanimous readings",
                    value: percent(consensus.agreement_share["4"] ?? 0, 2),
                  },
                  {
                    key: "Reference vote rate",
                    value: percent(consensus.reference_vote_rates["pca_vote"] ?? 0, 1),
                  },
                ]}
              />
              <p
                style={{
                  marginTop: "0.9rem",
                  fontSize: "0.8125rem",
                  color: "var(--ink-3)",
                  lineHeight: 1.55,
                }}
              >
                The quantile is deliberately conservative. A threshold at the 95th percentile would
                flag 5% of healthy data by construction before any real anomaly is seen.
              </p>
            </div>
          </BlurFade>
        </div>
      </Section>

      <Section
        title="Features"
        note={`${card.features.count} features per reading, standardised per station on the reference period.`}
      >
        <div className="split">
          <BlurFade delay={0.02} duration={0.32} offset={14}>
            <div className="card card-pad">
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                {card.features.columns.map((column) => (
                  <span
                    key={column}
                    className="chip"
                    data-tone="neutral"
                    style={{ fontSize: "0.75rem", padding: "0.25rem 0.55rem" }}
                  >
                    {column.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
              <p
                style={{
                  marginTop: "1rem",
                  fontSize: "0.8125rem",
                  color: "var(--ink-3)",
                  lineHeight: 1.55,
                }}
              >
                {card.features.scaling}. Every column is computed from{" "}
                <em style={{ fontStyle: "normal", fontWeight: 550, color: "var(--ink)" }}>
                  measured values only
                </em>{" "}
                — `clean_value` never enters the model.
              </p>
            </div>
          </BlurFade>

          <BlurFade delay={0.06} duration={0.32} offset={14}>
            <div className="card card-pad">
              <h3 className="card-title" style={{ marginBottom: "0.75rem" }}>
                Dataset
              </h3>
              <KvList
                rows={[
                  { key: "Source", value: "Open-Meteo / ERA5" },
                  { key: "Window", value: "2023, hourly" },
                  { key: "Stations", value: String(dataset.stations.length) },
                  { key: "Sensors", value: String(dataset.sensors.length) },
                  { key: "Fault coverage", value: percent(dataset.fault_coverage, 2) },
                  { key: "Extreme coverage", value: percent(dataset.extreme_coverage, 2) },
                  { key: "Reference fraction", value: percent(dataset.reference_fraction, 0) },
                ]}
              />
            </div>
          </BlurFade>
        </div>
      </Section>

      <Section
        title="Accuracy, split the way the problem demands"
        note="Faults and extremes are scored separately. Averaging them would hide the entire point."
      >
        <div className="cols-2">
          <BlurFade delay={0.02} duration={0.32} offset={16}>
            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">Recall by fault type</h3>
                  <p className="card-caption">consensus versus the fixed range check</p>
                </div>
              </div>
              <div style={{ padding: "0.5rem 1rem 1rem" }}>
                <RecallBars
                  detector={card.per_fault_type_recall}
                  baseline={card.baseline_per_fault_type_recall}
                />
              </div>
            </div>
          </BlurFade>

          <BlurFade delay={0.06} duration={0.32} offset={16}>
            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">Flag rate by ground-truth class</h3>
                  <p className="card-caption">how much of each class the detector calls anomalous</p>
                </div>
              </div>
              <div style={{ padding: "0.5rem 1rem 1rem" }}>
                <FlagRateBars confusion={card.confusion} />
              </div>
            </div>
          </BlurFade>
        </div>
      </Section>

      <Section title="Metric table" note="Every headline number, detector against baseline.">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <div className="card-flat">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th style={{ textAlign: "right" }}>Consensus</th>
                    <th style={{ textAlign: "right" }}>Range check</th>
                    <th style={{ textAlign: "right" }}>Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    {
                      name: "Fault detection rate",
                      detector: card.detector.fault_detection_rate,
                      baseline: card.baseline_range_check.fault_detection_rate,
                      higher: true,
                    },
                    {
                      name: "Fault classification rate",
                      detector: card.detector.fault_classification_rate,
                      baseline: card.baseline_range_check.fault_classification_rate,
                      higher: true,
                    },
                    {
                      name: "Extreme false-flag rate",
                      detector: card.detector.extreme_false_flag_rate,
                      baseline: card.baseline_range_check.extreme_false_flag_rate,
                      higher: false,
                    },
                    {
                      name: "Precision (fault class)",
                      detector: card.detector.precision,
                      baseline: card.baseline_range_check.precision,
                      higher: true,
                    },
                    {
                      name: "Recall (fault class)",
                      detector: card.detector.recall,
                      baseline: card.baseline_range_check.recall,
                      higher: true,
                    },
                    {
                      name: "F1 (fault class)",
                      detector: card.detector.f1,
                      baseline: card.baseline_range_check.f1,
                      higher: true,
                    },
                    {
                      name: "False positives on clean",
                      detector: card.detector.false_positive_rate_clean,
                      baseline: card.baseline_range_check.false_positive_rate_clean,
                      higher: false,
                    },
                    {
                      name: "Precision @ 10",
                      detector: card.detector.precision_at_k["10"],
                      baseline: card.baseline_range_check.precision_at_k["10"],
                      higher: true,
                    },
                    {
                      name: "Precision @ 25",
                      detector: card.detector.precision_at_k["25"],
                      baseline: card.baseline_range_check.precision_at_k["25"],
                      higher: true,
                    },
                    {
                      name: "Precision @ 50",
                      detector: card.detector.precision_at_k["50"],
                      baseline: card.baseline_range_check.precision_at_k["50"],
                      higher: true,
                    },
                  ].map((row) => {
                    const diff = row.detector - row.baseline;
                    const winner =
                      Math.abs(diff) < 1e-9
                        ? "tie"
                        : row.higher
                          ? diff > 0
                            ? "detector"
                            : "baseline"
                          : diff < 0
                            ? "detector"
                            : "baseline";
                    const detWins = winner === "detector";
                    return (
                      <tr key={row.name}>
                        <td className="cell-strong">{row.name}</td>
                        <td
                          style={{ textAlign: "right" }}
                          className={detWins ? "cell-strong" : undefined}
                        >
                          {row.detector.toFixed(4)}
                        </td>
                        <td
                          style={{ textAlign: "right" }}
                          className={detWins ? "cell-muted" : "cell-strong"}
                        >
                          {row.baseline.toFixed(4)}
                        </td>
                        <td style={{ textAlign: "right" }} className="cell-muted">
                          {diff > 0 ? "+" : ""}
                          {diff.toFixed(4)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </BlurFade>
      </Section>

      <Section title="Unsupervised by construction" note="Three mechanisms, not a promise.">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <div className="card card-pad">
            <Callout icon={<ShieldCheck size={17} weight="regular" />}>
              <strong style={{ color: "var(--ink)", fontWeight: 550 }}>
                {card.supervision.training_labels_used} training labels used.
              </strong>{" "}
              {card.supervision.label_source}. {card.supervision.guard}.
            </Callout>
            <div style={{ marginTop: "1rem" }}>
              <StepList
                steps={[
                  {
                    title: "Stripped at load",
                    body: "run_experiment.py drops every label column before feature code runs.",
                  },
                  {
                    title: "Guard raises",
                    body: "leakage_guard.py raises if a label reaches a feature frame, detector input or detector output.",
                  },
                  {
                    title: "Tests prove it",
                    body: "test_leakage_guard asserts the guard fires on a labelled frame and passes on a clean one.",
                  },
                  {
                    title: "No model imports a label",
                    body: "nothing in src/algorithms reads, receives or infers a ground-truth column.",
                  },
                ]}
              />
            </div>
          </div>
        </BlurFade>
      </Section>

      <Section title="Pipeline timing" note="Measured on this machine, full year, all stations.">
        <div className="cols-3">
          {[
            { label: "Feature build", value: card.runtime.features_seconds ?? 0, unit: "s" },
            { label: "Detectors", value: card.runtime.detector_seconds ?? 0, unit: "s" },
            { label: "Discriminator", value: card.runtime.discriminator_seconds ?? 0, unit: "s" },
          ].map((item, index) => (
            <BlurFade key={item.label} delay={index * 0.05} duration={0.32} offset={12}>
              <div className="card card-pad">
                <p className="mono-label">{item.label}</p>
                <p
                  style={{
                    fontSize: "1.75rem",
                    fontWeight: 500,
                    letterSpacing: "-0.04em",
                    marginTop: "0.3rem",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  <TickedNumber value={item.value} decimals={2} suffix={item.unit} />
                </p>
              </div>
            </BlurFade>
          ))}
        </div>
      </Section>

      <Section title="Where to look next">
        <div className="cols-3">
          {[
            {
              href: "/events",
              title: "Detection events",
              body: "Episodes with the reason code that decided fault or extreme.",
            },
            {
              href: "/stations",
              title: "Station health",
              body: "Per-site status, fault counts and hourly traces.",
            },
            {
              href: "/method",
              title: "Method notes",
              body: "Fault and extreme models, the rule tree, and the baseline definition.",
            },
          ].map((item, index) => (
            <BlurFade key={item.href} delay={index * 0.05} duration={0.32} offset={12}>
              <Link href={item.href} className="card card-pad" style={{ display: "block" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "0.5rem",
                  }}
                >
                  <span className="card-title">{item.title}</span>
                  <ArrowUpRight size={15} weight="bold" style={{ color: "var(--ink-3)" }} />
                </div>
                <p style={{ marginTop: "0.5rem", color: "var(--ink-3)", fontSize: "0.875rem" }}>
                  {item.body}
                </p>
              </Link>
            </BlurFade>
          ))}
        </div>
      </Section>
    </>
  );
}
