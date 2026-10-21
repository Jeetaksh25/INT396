import Link from "next/link";
import { ArrowUpRight, WarningCircle } from "@phosphor-icons/react/dist/ssr";
import { getMetrics } from "@/lib/api";
import { MetricsSummary } from "@/lib/types";
import { PageHead, Section, StepList, Callout, KvList } from "@/components/page-parts";
import { TopBar } from "@/components/top-bar";
import { BlurFade } from "@/components/ui/blur-fade";

const percent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;

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
      <>
        <TopBar />
        <PageHead title="Method" description="Metrics could not be loaded." />
        <div className="error-panel">
          <h2 className="error-title">Metrics unavailable</h2>
          <p className="code-line">{error}</p>
        </div>
      </>
    );
  }

  return (
    <>
      <TopBar />
      <PageHead
        size="large"
        title="How a reading is judged"
        description="Five detectors vote, a threshold decides, and a transparent rule tree separates a failing instrument from real weather. The fixed range check runs beside it as the mandatory baseline."
        aside={
          <>
            <span>{metrics.label_counts.total_readings.toLocaleString()} readings</span>
            <span>seed {metrics.random_seed} · {metrics.rule_count} rules</span>
          </>
        }
      />

      <Section title="The pipeline, in order" note="Five stages, no hidden step.">
        <BlurFade delay={0.02} duration={0.6} offset={14}>
          <div className="card card-pad">
            <StepList
              steps={[
                {
                  title: "Simulate faults and extremes",
                  body: (
                    <>
                      Six fault types injected on a single sensor per episode; four extreme types
                      injected coherently across every sensor of a station. Labels are written, then
                      hidden from the model.
                    </>
                  ),
                },
                {
                  title: "Build features",
                  body: (
                    <>
                      Ten features per reading, standardised per station on the first 30% of the
                      timeline. <span className="cell-muted">clean_value</span> never enters.
                    </>
                  ),
                },
                {
                  title: "Vote",
                  body: (
                    <>
                      Each detector scores every reading; each score is compared against its own
                      reference-period quantile. Three or more votes mark an anomaly — two was
                      tested and traded too much precision for recall.
                    </>
                  ),
                },
                {
                  title: "Group and discriminate",
                  body: (
                    <>
                      Consecutive flagged hours become an episode. Coherence, neighbour agreement and
                      a physics check decide FAULT or EXTREME.
                    </>
                  ),
                },
                {
                  title: "Score against the baseline",
                  body: (
                    <>
                      Every metric is computed twice with identical code — once for the consensus,
                      once for fixed range limits.
                    </>
                  ),
                },
              ]}
            />
          </div>
        </BlurFade>
      </Section>

      <Section title="Fault and extreme models" note="What was injected, and why it is separable.">
        <div className="cols-2">
          <BlurFade delay={0.02} duration={0.6} offset={14}>
            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">Injected faults</h3>
                  <p className="card-caption">single sensor, single station per episode</p>
                </div>
                <span className="chip" data-tone="down">
                  {percent(metrics.label_counts.fault_readings / metrics.label_counts.total_readings, 2)}
                </span>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Fault</th>
                      <th>Mechanism</th>
                      <th style={{ textAlign: "right" }}>Recall</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(metrics.per_fault_type_recall).map(([name, recall]) => (
                      <tr key={name}>
                        <td className="cell-strong">{name}</td>
                        <td className="cell-muted">
                          {{
                            bias: "constant offset, 3–8σ",
                            drift: "linear ramp, 2–5σ",
                            stuck: "frozen value",
                            spike: "isolated jumps, 5–12σ",
                            precision: "quantisation + noise",
                            dropout: "missing values",
                          }[name] ?? "injected"}
                        </td>
                        <td style={{ textAlign: "right" }}>{percent(recall)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </BlurFade>

          <BlurFade delay={0.06} duration={0.6} offset={14}>
            <div className="card card-pad">
              <h3 className="card-title" style={{ marginBottom: "0.6rem" }}>
                Why the two are separable
              </h3>
              <div className="note-list">
                <p>
                  A faulty sensor breaks physical consistency: its reading is impossible, or it
                  deviates alone while the other three sensors at the same station stay normal.
                </p>
                <p>
                  A genuine extreme is extreme but consistent: several sensors move together, and
                  nearby stations usually see the same weather.
                </p>
                <p>
                  The decisive measured signal is the coherence ratio — deviation of the other sensors
                  divided by deviation of the flagged one.
                </p>
              </div>
              <div style={{ marginTop: "1rem" }}>
                <Callout icon={<WarningCircle size={17} weight="regular" />}>
                  The discriminator is a transparent rule tree, not a classifier. That keeps it
                  explainable, and it also means a novel fault that happens to move several sensors
                  coherently would be called an extreme.
                </Callout>
              </div>
            </div>
          </BlurFade>
        </div>
      </Section>

      <Section title="The rule tree" note="Read top to bottom, first match wins.">
        <BlurFade delay={0.02} duration={0.6} offset={14}>
          <div className="card card-pad">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th style={{ width: "3rem" }}>#</th>
                    <th>Condition</th>
                    <th>Verdict</th>
                    <th>Reason code</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Any hard physical rule violated", "FAULT", "physics_inconsistent"],
                    ["Other sensors deviate proportionally to the flagged one", "EXTREME", "coherent_multi_sensor"],
                    ["Coherent and neighbouring stations agree", "EXTREME", "coherent_regional"],
                    ["Stable deviation past the sustained threshold", "EXTREME", "sustained_regime"],
                    ["Single sensor deviates, neighbours normal", "FAULT", "isolated_sensor"],
                    ["Nothing above matched", "FAULT", "isolated_or_erratic"],
                  ].map(([condition, verdict, reason], index) => (
                    <tr key={reason}>
                      <td className="cell-muted">{index + 1}</td>
                      <td>{condition}</td>
                      <td>
                        <span
                          className="chip"
                          data-tone={verdict === "FAULT" ? "down" : "accent"}
                        >
                          {verdict}
                        </span>
                      </td>
                      <td className="cell-muted">{reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </BlurFade>
      </Section>

      <Section title="Baseline definition" note="The naive quality-control rule every network already runs.">
        <div className="split">
          <BlurFade delay={0.02} duration={0.6} offset={14}>
            <div className="card-flat">
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Sensor</th>
                      <th style={{ textAlign: "right" }}>Min</th>
                      <th style={{ textAlign: "right" }}>Max</th>
                      <th>Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["temperature", -5, 45, "°C"],
                      ["humidity", 0, 100, "%"],
                      ["wind_speed", 0, 120, "km/h"],
                      ["pressure", 950, 1050, "hPa"],
                    ].map(([sensor, low, high, unit]) => (
                      <tr key={String(sensor)}>
                        <td className="cell-strong">{String(sensor).replace("_", " ")}</td>
                        <td style={{ textAlign: "right" }}>{low}</td>
                        <td style={{ textAlign: "right" }}>{high}</td>
                        <td className="cell-muted">{unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </BlurFade>

          <BlurFade delay={0.06} duration={0.6} offset={14}>
            <div className="card card-pad">
              <h3 className="card-title" style={{ marginBottom: "0.6rem" }}>
                Baseline versus consensus
              </h3>
              <KvList
                rows={[
                  {
                    key: "Fault detection",
                    value: `${percent(metrics.baseline_range_check.fault_detection_rate)} → ${percent(metrics.detector.fault_detection_rate)}`,
                  },
                  {
                    key: "F1",
                    value: `${metrics.baseline_range_check.f1.toFixed(3)} → ${metrics.detector.f1.toFixed(3)}`,
                  },
                  {
                    key: "Precision at 50",
                    value: `${percent(metrics.baseline_range_check.precision_at_k["50"])} → ${percent(metrics.detector.precision_at_k["50"])}`,
                  },
                  {
                    key: "Clean false positives",
                    value: `${percent(metrics.baseline_range_check.false_positive_rate_clean, 2)} → ${percent(metrics.detector.false_positive_rate_clean, 2)}`,
                  },
                ]}
              />
              <p style={{ marginTop: "0.9rem", fontSize: "0.8125rem", color: "var(--ink-3)", lineHeight: 1.55 }}>
                The baseline keeps perfect precision because it flags so little. The consensus is
                deliberately more aggressive: it catches failure modes a range check cannot see at
                all.
              </p>
            </div>
          </BlurFade>
        </div>
      </Section>

      <Section title="Where the numbers come from" note="Every metric is reproducible from one command.">
        <div className="cols-3">
          {[
            {
              href: "/model",
              title: "Model card",
              body: "Per-detector hyperparameters, vote distribution, leakage guard.",
            },
            {
              href: "/events",
              title: "Detection events",
              body: "Every episode with its reason code and score.",
            },
            {
              href: "/stations",
              title: "Station health",
              body: "Per-site status and hourly traces.",
            },
          ].map((item, index) => (
            <BlurFade key={item.href} delay={index * 0.05} duration={0.6} offset={12}>
              <Link href={item.href} className="card card-pad" style={{ display: "block" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
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
