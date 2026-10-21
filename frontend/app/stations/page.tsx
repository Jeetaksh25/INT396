import Link from "next/link";
import { getMetrics, getStations } from "@/lib/api";
import { MetricsSummary, StationHealth } from "@/lib/types";
import { StatusBadge } from "@/components/badges";

export const dynamic = "force-dynamic";

function statusRank(status: StationHealth["status"]) {
  const order = { FAULT: 0, EXTREME_EVENT: 1, WATCH: 2, HEALTHY: 3 };
  return order[status] ?? 4;
}

export default async function StationsPage() {
  let stations: StationHealth[] = [];
  let metrics: MetricsSummary | null = null;
  let error: string | null = null;

  try {
    [stations, metrics] = await Promise.all([getStations(), getMetrics()]);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "unknown error";
  }

  if (error) {
    return (
      <div className="error-panel" style={{ marginTop: "2rem" }}>
        <h2 className="error-title">Station data unavailable</h2>
        <p className="code-line">{error}</p>
      </div>
    );
  }

  const sorted = [...stations].sort(
    (a, b) => statusRank(a.status) - statusRank(b.status) || a.station_id.localeCompare(b.station_id),
  );

  return (
    <>
      <header className="page-head">
        <div>
          <h1 className="page-title">Station integrity</h1>
          <p className="page-sub">
            Every site is judged on its trailing week: faults first, then genuine extremes, then
            elevated anomaly density. Click a station for its hourly trace.
          </p>
        </div>
        <div className="stamp">
          <div>{stations.length} stations</div>
          <div>{metrics ? `${metrics.label_counts.total_readings.toLocaleString()} readings` : "—"}</div>
        </div>
      </header>

      <section className="section">
        <div className="panel-flush scroll-x">
          <table className="table">
            <thead>
              <tr>
                <th>Station</th>
                <th>Status</th>
                <th>Fault events</th>
                <th>Extreme events</th>
                <th>Anomalous share</th>
                <th>Total events</th>
                <th>Fault recall</th>
                <th>Last reading</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((station) => {
                const stationMetrics = metrics?.per_station[station.station_id];
                return (
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
                    <td className="mono">{station.total_events}</td>
                    <td className="mono">
                      {stationMetrics
                        ? `${(stationMetrics.fault_detection_rate * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="mono" style={{ color: "var(--ink-3)" }}>
                      {new Date(station.last_reading_at).toLocaleDateString("en-GB", {
                        day: "2-digit",
                        month: "short",
                      })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
