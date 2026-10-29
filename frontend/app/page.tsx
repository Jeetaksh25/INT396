import Link from "next/link";
import { ArrowUpRight, WarningCircle } from "@phosphor-icons/react/dist/ssr";
import { getMetrics, getStations, getTimeline } from "@/lib/api";
import { MetricsSummary, StationHealth, TimelinePoint } from "@/lib/types";
import { NetworkTimeline } from "@/components/charts";
import { StatusBadge } from "@/components/badges";
import { PageHead, MetricCard, Section, TickedNumber } from "@/components/page-parts";
import { TopBar } from "@/components/top-bar";
import { BlurFade } from "@/components/ui/blur-fade";

const statusRank = (status: StationHealth["status"]) =>
  ({ FAULT: 0, EXTREME_EVENT: 1, WATCH: 2, HEALTHY: 3 })[status] ?? 4;

const percent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;

async function loadOverview() {
  const [metrics, stations, timeline] = await Promise.all([
    getMetrics(),
    getStations(),
    getTimeline(30),
  ]);
  return { metrics, stations, timeline };
}

function HeroBand({
  metrics,
  stations,
}: {
  metrics: MetricsSummary;
  stations: StationHealth[];
}) {
  const faultStations = stations.filter((station) => station.status === "FAULT").length;
  const extremeStations = stations.filter((station) => station.status === "EXTREME_EVENT").length;

  return (
    <div className="hero-band">
      <div>
        <BlurFade delay={0.02} duration={0.32} offset={16}>
          <h1 className="page-title-lg">Which instruments are lying to you?</h1>
        </BlurFade>
        <BlurFade delay={0.08} duration={0.32} offset={14}>
          <p className="page-sub" style={{ maxWidth: "48ch" }}>
            Eight Indian weather stations, one year of hourly ERA5 readings, four unsupervised
            detectors in a vote, and a small supervised booster that tells a broken sensor apart
            from a real heat wave.
          </p>
        </BlurFade>
      </div>
      <div className="hero-stats">
        <div className="hero-stat">
          <span className="hero-stat-value">
            <TickedNumber value={stations.length} />
          </span>
          <span className="hero-stat-key">stations monitored</span>
        </div>
        <div className="hero-stat">
          <span className="hero-stat-value">
            <TickedNumber value={metrics.label_counts.total_readings} />
          </span>
          <span className="hero-stat-key">hourly readings</span>
        </div>
        <div className="hero-stat">
          <span className="hero-stat-value">
            {faultStations} / {extremeStations}
          </span>
          <span className="hero-stat-key">fault / extreme stations</span>
        </div>
        <div className="hero-stat">
          <span className="hero-stat-value">
            <TickedNumber value={metrics.grouped.accuracy * 100} decimals={1} suffix="%" />
          </span>
          <span className="hero-stat-key">boosted accuracy, unseen stations</span>
        </div>
      </div>
    </div>
  );
}

export default async function HomePage() {
  let data: Awaited<ReturnType<typeof loadOverview>> | null = null;
  let error: string | null = null;

  try {
    data = await loadOverview();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "unknown error";
  }

  if (error || !data) {
    return (
      <>
        <TopBar />
        <PageHead
          title="Network overview"
          description="The dashboard reads pre-computed results from the FastAPI service."
        />
        <div className="error-panel">
          <h2 className="error-title">Backend results are not reachable</h2>
          <p style={{ color: "var(--ink-2)" }}>
            Start the API, then reload this page.
          </p>
          <p className="code-line">cd backend &amp;&amp; python -m uvicorn main:app --port 8000</p>
          <p className="code-line">{error}</p>
        </div>
      </>
    );
  }

  const { metrics, stations, timeline } = data;
  const sortedStations = [...stations].sort(
    (a, b) =>
      statusRank(a.status) - statusRank(b.status) || a.station_id.localeCompare(b.station_id),
  );
  const points: TimelinePoint[] = timeline.points.slice(-720);

  return (
    <>
      <TopBar />
      <HeroBand metrics={metrics} stations={stations} />

      <div className="metric-grid" style={{ marginTop: "1.75rem" }}>
        <MetricCard
          label="Unsupervised accuracy"
          value={metrics.unsupervised.grouped.accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          caption={`detectors alone · macro F1 ${metrics.unsupervised.grouped.macro_f1.toFixed(3)}`}
          delay={0.02}
        />
        <MetricCard
          label="Boosted accuracy"
          value={metrics.grouped.accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          delta={metrics.grouped.accuracy - metrics.unsupervised.grouped.accuracy}
          caption="with the supervised booster"
          delay={0.04}
        />
        <MetricCard
          label="Boosted balanced accuracy"
          value={metrics.grouped.balanced_accuracy}
          format="percent"
          decimals={1}
          suffix="%"
          caption={`unsupervised ${percent(metrics.unsupervised.grouped.balanced_accuracy)}`}
          delay={0.06}
        />
        <MetricCard
          label="Boosted macro F1"
          value={metrics.grouped.macro_f1}
          decimals={3}
          delta={metrics.grouped.macro_f1 - metrics.unsupervised.grouped.macro_f1}
          caption={`range check ${metrics.range_check.macro_f1.toFixed(3)}`}
          delay={0.1}
        />
      </div>

      <Section
        title="Network activity"
        note="Flagged readings across all eight stations, aggregated by day. Switch to 7 days for the hourly view."
      >
        <BlurFade delay={0.02} duration={0.32} offset={16}>
          <div className="card card-pad">
            <NetworkTimeline points={points} days={30} />
          </div>
        </BlurFade>
      </Section>

      <Section
        title="Station health"
        note="Trailing 30 days: faults first, then genuine extremes, then flag density."
        action={
          <Link href="/stations" className="btn">
            All stations
            <ArrowUpRight size={14} weight="bold" />
          </Link>
        }
      >
        <BlurFade delay={0.02} duration={0.32} offset={16}>
          <div className="card-flat">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Station</th>
                    <th>Status</th>
                    <th style={{ textAlign: "right" }}>Faults</th>
                    <th style={{ textAlign: "right" }}>Extremes</th>
                    <th style={{ textAlign: "right" }}>Anomalous</th>
                    <th>Last fault</th>
                    <th aria-label="Open" />
                  </tr>
                </thead>
                <tbody>
                  {sortedStations.map((station) => (
                    <tr key={station.station_id}>
                      <td>
                        <Link href={`/stations/${station.station_id}`} className="station-cell">
                          <span className="station-id">{station.station_id}</span>
                          <span className="station-name">
                            <span className="cell-strong">{station.station_name}</span>
                            <small>{station.total_events} events on record</small>
                          </span>
                        </Link>
                      </td>
                      <td>
                        <StatusBadge status={station.status} />
                      </td>
                      <td style={{ textAlign: "right" }} className="cell-strong">
                        {station.fault_events}
                      </td>
                      <td style={{ textAlign: "right" }} className="cell-strong">
                        {station.extreme_events}
                      </td>
                      <td style={{ textAlign: "right" }}>{station.anomalous_percent.toFixed(2)}%</td>
                      <td className="cell-muted">{station.last_fault_type ?? "—"}</td>
                      <td style={{ textAlign: "right" }}>
                        <Link
                          href={`/stations/${station.station_id}`}
                          className="row-link"
                          aria-label={`Open ${station.station_name}`}
                        >
                          <ArrowUpRight size={14} weight="bold" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </BlurFade>
      </Section>

      <Section title="Where the evidence lives" note="Three views of the same pipeline.">
        <div className="cols-3">
          {[
            {
              href: "/stations",
              title: "Stations",
              body: "Ranked by trailing-window health, then opened hour-by-hour per sensor.",
            },
            {
              href: "/events",
              title: "Events",
              body: "Consecutive flagged hours grouped into episodes, with the class the forest predicted.",
            },
            {
              href: "/model",
              title: "Model card",
              body: "The four detectors, the booster, per-class scores and both confusion matrices.",
            },
          ].map((item, index) => (
            <BlurFade key={item.href} delay={index * 0.05} duration={0.32} offset={14}>
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
                <p style={{ marginTop: "0.5rem", color: "var(--ink-3)", fontSize: "0.875rem", lineHeight: 1.55 }}>
                  {item.body}
                </p>
              </Link>
            </BlurFade>
          ))}
        </div>
      </Section>

      <Section title="Read this before quoting a number" note="The honest caveats, stated up front.">
        <BlurFade delay={0.02} duration={0.32} offset={14}>
          <div className="card card-pad">
            <div className="note-list">
              <p>
                <WarningCircle
                  size={16}
                  weight="regular"
                  style={{ display: "inline", marginRight: "0.4rem", color: "var(--watch)" }}
                  aria-hidden="true"
                />
                Faults and extremes are injected into real ERA5 readings, so every label is known.
                Real failure logs are not public, which makes these numbers optimistic for a live
                network.
              </p>
              <p>
                Most readings are normal, so always predicting &quot;normal&quot; already scores{" "}
                {percent(metrics.majority_baseline)}. Balanced accuracy (
                {percent(metrics.grouped.balanced_accuracy)}) and macro F1 show the real gain.
              </p>
              <p>
                Every score comes from stations the model never trained on.{" "}
                <Link href="/model" className="row-link">
                  See the evaluation
                </Link>
                .
              </p>
            </div>
          </div>
        </BlurFade>
      </Section>
    </>
  );
}
