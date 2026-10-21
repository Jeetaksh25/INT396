import Link from "next/link";
import { getMetrics, getStations, getTimeline } from "@/lib/api";
import { MetricBlock, MetricsSummary, StationHealth, TimelinePoint } from "@/lib/types";
import { NetworkTimeline } from "@/components/charts";
import { StatusBadge } from "@/components/badges";

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function deltaLabel(value: number, unit = "pp") {
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(1)}${unit}`;
}

function StatCell({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      <span className="stat-delta">{detail}</span>
    </div>
  );
}

function MetricSummaryBlock({ metrics }: { metrics: MetricsSummary }) {
  const detector: MetricBlock = metrics.detector;
  const baseline: MetricBlock = metrics.baseline_range_check;
  const topK = detector.precision_at_k;

  return (
    <div className="stat-strip">
      <StatCell
        label="Fault detection rate"
        value={percent(detector.fault_detection_rate)}
        detail={`baseline ${percent(baseline.fault_detection_rate)} · ${deltaLabel(
          metrics.delta.fault_detection_rate,
        )}`}
      />
      <StatCell
        label="Extreme false-flag rate"
        value={percent(detector.extreme_false_flag_rate)}
        detail={`baseline ${percent(baseline.extreme_false_flag_rate)} · lower is better`}
      />
      <StatCell
        label={`Precision @ ${Object.keys(topK)[0]}`}
        value={percent(topK[Object.keys(topK)[0]] ?? 0)}
        detail={`P@25 ${percent(topK["25"] ?? 0)} · P@50 ${percent(topK["50"] ?? 0)}`}
      />
      <StatCell
        label="F1 on fault class"
        value={detector.f1.toFixed(3)}
        detail={`precision ${detector.precision.toFixed(3)} · recall ${detector.recall.toFixed(3)}`}
      />
      <StatCell
        label="Clean-data alarm rate"
        value={percent(detector.false_positive_rate_clean)}
        detail={`baseline ${percent(baseline.false_positive_rate_clean)}`}
      />
    </div>
  );
}

function statusRank(status: StationHealth["status"]) {
  const order = { FAULT: 0, EXTREME_EVENT: 1, WATCH: 2, HEALTHY: 3 };
  return order[status] ?? 4;
}

async function loadOverview() {
  const [metrics, stations, timeline] = await Promise.all([
    getMetrics(),
    getStations(),
    getTimeline(30),
  ]);
  return { metrics, stations, timeline };
}

export async function NetworkOverview() {
  let data: Awaited<ReturnType<typeof loadOverview>> | null = null;
  let error: string | null = null;

  try {
    data = await loadOverview();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "unknown error";
  }

  if (error || !data) {
    return (
      <div className="section">
        <div className="error-panel">
          <h2 className="error-title">Backend results are not reachable</h2>
          <p style={{ color: "var(--ink-2)" }}>
            The dashboard reads pre-computed results from the FastAPI service. Start it and reload.
          </p>
          <p className="code-line">cd backend &amp;&amp; python -m uvicorn main:app --port 8000</p>
          <p className="code-line">{error}</p>
        </div>
      </div>
    );
  }

  const sortedStations = [...data.stations].sort(
    (a, b) => statusRank(a.status) - statusRank(b.status) || a.station_id.localeCompare(b.station_id),
  );
  const points: TimelinePoint[] = data.timeline.points.slice(-720);
  const faultStations = data.stations.filter((station) => station.status === "FAULT").length;
  const extremeStations = data.stations.filter(
    (station) => station.status === "EXTREME_EVENT",
  ).length;

  return (
    <>
      <MetricSummaryBlock metrics={data.metrics} />

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">Network activity, last 30 days</h2>
          <div className="legend">
            <span className="legend-item">
              <span className="swatch" style={{ background: "oklch(76% 0.145 68)" }} />
              flagged readings per hour
            </span>
            <span className="legend-item mono">
              {faultStations} fault · {extremeStations} extreme · {data.stations.length} total
            </span>
          </div>
        </div>
        <div className="panel">
          <NetworkTimeline points={points} />
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">Station health</h2>
          <span className="section-note">
            trailing {data.stations[0]?.window_hours ?? 168} hours
          </span>
        </div>
        <div className="panel-flush scroll-x">
          <table className="table">
            <thead>
              <tr>
                <th>Station</th>
                <th>Status</th>
                <th>Faults</th>
                <th>Extremes</th>
                <th>Anomalous</th>
                <th>Last fault</th>
              </tr>
            </thead>
            <tbody>
              {sortedStations.map((station) => (
                <tr key={station.station_id}>
                  <td>
                    <Link href={`/stations/${station.station_id}`} className="row-link">
                      <span className="mono">{station.station_id}</span>
                      {station.station_name}
                    </Link>
                  </td>
                  <td>
                    <StatusBadge status={station.status} />
                  </td>
                  <td className="mono">{station.fault_events}</td>
                  <td className="mono">{station.extreme_events}</td>
                  <td className="mono">{station.anomalous_percent.toFixed(2)}%</td>
                  <td className="mono" style={{ color: "var(--ink-3)" }}>
                    {station.last_fault_type ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
