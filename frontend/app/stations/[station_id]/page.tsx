import { notFound } from "next/navigation";
import Link from "next/link";
import { getStationDetail, getStationSeries } from "@/lib/api";
import { StationDetail, StationSeries } from "@/lib/types";
import { StatusBadge, SensorName } from "@/components/badges";
import { StationSeriesPanel } from "@/components/station-series";

export const dynamic = "force-dynamic";

const stationNames: Record<string, string> = {
  DEL: "Delhi",
  BOM: "Mumbai",
  MAA: "Chennai",
  HYD: "Hyderabad",
  JAI: "Jaipur",
  CCU: "Kolkata",
  BLR: "Bengaluru",
  SLM: "Shimla",
};

export default async function StationPage({
  params,
}: {
  params: Promise<{ station_id: string }>;
}) {
  const { station_id } = await params;

  let detail: StationDetail;
  let series: StationSeries;

  try {
    [detail, series] = await Promise.all([
      getStationDetail(station_id, 168),
      getStationSeries(station_id, 30),
    ]);
  } catch {
    notFound();
  }

  const station = detail.station;
  const stationName = stationNames[station_id] ?? station.station_name;

  return (
    <>
      <header className="page-head">
        <div>
          <h1 className="page-title">
            {stationName} <span className="mono" style={{ fontSize: "0.4em", color: "var(--ink-3)" }}>{station_id}</span>
          </h1>
          <p className="page-sub">
            Last {series.days} days of readings with flagged hours, plus the trailing-week event
            summary that drives the network status.
          </p>
        </div>
        <div className="stamp">
          <div>
            <StatusBadge status={station.status} />
          </div>
          <div style={{ marginTop: "0.4rem" }}>
            {station.latitude.toFixed(2)}, {station.longitude.toFixed(2)}
          </div>
        </div>
      </header>

      <section className="section" style={{ paddingTop: "1.5rem" }}>
        <div className="detail-grid">
          <div className="detail-cell">
            <div className="detail-key">Fault events</div>
            <div className="detail-value mono">{station.fault_events}</div>
          </div>
          <div className="detail-cell">
            <div className="detail-key">Extreme events</div>
            <div className="detail-value mono">{station.extreme_events}</div>
          </div>
          <div className="detail-cell">
            <div className="detail-key">Anomalous share</div>
            <div className="detail-value mono">{station.anomalous_percent.toFixed(2)}%</div>
          </div>
          <div className="detail-cell">
            <div className="detail-key">Total events</div>
            <div className="detail-value mono">{station.total_events}</div>
          </div>
          <div className="detail-cell">
            <div className="detail-key">Last fault</div>
            <div className="detail-value mono">{station.last_fault_type ?? "—"}</div>
          </div>
          <div className="detail-cell">
            <div className="detail-key">Window</div>
            <div className="detail-value mono">{station.window_hours}h</div>
          </div>
        </div>
      </section>

      <StationSeriesPanel series={series} />

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">Sensor summary, trailing week</h2>
          <span className="section-note">window {detail.window_start.slice(0, 16)} → {detail.window_end.slice(0, 16)}</span>
        </div>
        <div className="grid-two">
          <div className="panel-flush scroll-x">
            <table className="table">
              <thead>
                <tr>
                  <th>Sensor</th>
                  <th>Readings</th>
                  <th>Anomalies</th>
                  <th>Fault flags</th>
                  <th>Extreme flags</th>
                  <th>Mean</th>
                  <th>Peak score</th>
                </tr>
              </thead>
              <tbody>
                {detail.sensor_summary.map((sensor) => (
                  <tr key={sensor.sensor_name}>
                    <td>
                      <SensorName sensorName={sensor.sensor_name} />
                    </td>
                    <td className="mono">{sensor.readings}</td>
                    <td className="mono">{sensor.anomalies}</td>
                    <td className="mono">{sensor.fault_flags}</td>
                    <td className="mono">{sensor.extreme_flags}</td>
                    <td className="mono">{sensor.mean_value.toFixed(1)}</td>
                    <td className="mono">{sensor.max_score.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>Fault reason codes</h3>
            {detail.fault_breakdown.length === 0 ? (
              <p style={{ color: "var(--ink-3)", fontSize: "0.875rem" }}>
                No fault-labelled detections in this window.
              </p>
            ) : (
              detail.fault_breakdown.map((row) => (
                <div key={row.reason_code} className="meter">
                  <div className="meter-head">
                    <span className="meter-name">{row.reason_code}</span>
                    <span className="mono">{row.count}</span>
                  </div>
                </div>
              ))
            )}
            <div style={{ marginTop: "1rem" }}>
              <Link href="/stations" className="row-link">
                ← All stations
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">Recent detections</h2>
          <span className="section-note">top 25 by anomaly score</span>
        </div>
        <div className="panel-flush scroll-x">
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Sensor</th>
                <th>Value</th>
                <th>Score</th>
                <th>Verdict</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {detail.recent_detections.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ color: "var(--ink-3)" }}>
                    No flagged readings in this window.
                  </td>
                </tr>
              ) : (
                detail.recent_detections.map((row, index) => (
                  <tr key={`${row.timestamp}-${row.sensor_name}-${index}`}>
                    <td className="mono">{row.timestamp.replace("T", " ").slice(0, 16)}</td>
                    <td>
                      <SensorName sensorName={row.sensor_name} />
                    </td>
                    <td className="mono">
                      {row.measured_value === null ? "NaN" : row.measured_value.toFixed(2)}
                    </td>
                    <td className="mono">{row.anomaly_score.toFixed(2)}</td>
                    <td className="mono">{row.event_label ?? "—"}</td>
                    <td className="mono" style={{ color: "var(--ink-3)" }}>
                      {row.reason_code ?? "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
