import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowUpRight } from "@phosphor-icons/react/dist/ssr";
import { getStationDetail, getStationSeries } from "@/lib/api";
import { StationDetail, StationSeries } from "@/lib/types";
import { StatusBadge } from "@/components/badges";
import { TopBar } from "@/components/top-bar";
import { StationSeriesPanel } from "@/components/station-series";
import { BlurFade } from "@/components/ui/blur-fade";

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
      <TopBar />
      <header className="page-head">
        <div className="page-head-copy">
          <BlurFade delay={0.02} duration={0.55} offset={14}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <span className="station-id" style={{ width: "2.6rem", height: "2.6rem" }}>
                {station_id}
              </span>
              <h1 className="page-title">{stationName}</h1>
              <StatusBadge status={station.status} />
            </div>
          </BlurFade>
          <BlurFade delay={0.08} duration={0.55} offset={12}>
            <p className="page-sub">
              Last {series.days} days of readings with flagged hours, plus the trailing-week summary
              that drives the network status.
            </p>
          </BlurFade>
        </div>
        <BlurFade delay={0.12} duration={0.5} offset={10}>
          <div className="page-aside">
            <span>
              {station.latitude.toFixed(2)}, {station.longitude.toFixed(2)}
            </span>
            <span>trailing {station.window_hours} hours</span>
            <Link href="/stations" className="btn" style={{ marginTop: "0.35rem" }}>
              <ArrowLeft size={13} weight="bold" />
              All stations
            </Link>
          </div>
        </BlurFade>
      </header>

      <BlurFade delay={0.04} duration={0.6} offset={14}>
        <div className="metric-grid">
          {[
            { label: "Fault events", value: station.fault_events, caption: "in window" },
            { label: "Extreme events", value: station.extreme_events, caption: "in window" },
            {
              label: "Anomalous share",
              value: station.anomalous_percent,
              caption: "% of readings",
            },
            { label: "Total events", value: station.total_events, caption: "year to date" },
          ].map((item) => (
            <div className="metric" key={item.label}>
              <div className="metric-top">
                <span className="metric-label">{item.label}</span>
              </div>
              <div className="metric-value">{item.value}</div>
              <div className="metric-foot">
                <span>{item.caption}</span>
              </div>
            </div>
          ))}
        </div>
      </BlurFade>

      <section className="section">
        <StationSeriesPanel series={series} />
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <h2 className="section-title">Sensor summary</h2>
            <p className="section-note" style={{ marginTop: "0.2rem" }}>
              {detail.window_start.slice(0, 16)} → {detail.window_end.slice(0, 16)}
            </p>
          </div>
        </div>
        <div className="split">
          <BlurFade delay={0.02} duration={0.6} offset={16}>
            <div className="card-flat">
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Sensor</th>
                      <th style={{ textAlign: "right" }}>Readings</th>
                      <th style={{ textAlign: "right" }}>Anomalies</th>
                      <th style={{ textAlign: "right" }}>Fault</th>
                      <th style={{ textAlign: "right" }}>Extreme</th>
                      <th style={{ textAlign: "right" }}>Mean</th>
                      <th style={{ textAlign: "right" }}>Peak score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.sensor_summary.map((sensor) => (
                      <tr key={sensor.sensor_name}>
                        <td className="cell-strong">{sensor.sensor_name.replace("_", " ")}</td>
                        <td style={{ textAlign: "right" }}>{sensor.readings}</td>
                        <td style={{ textAlign: "right" }}>{sensor.anomalies}</td>
                        <td style={{ textAlign: "right" }}>{sensor.fault_flags}</td>
                        <td style={{ textAlign: "right" }}>{sensor.extreme_flags}</td>
                        <td style={{ textAlign: "right" }}>{sensor.mean_value.toFixed(1)}</td>
                        <td style={{ textAlign: "right" }}>{sensor.max_score.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </BlurFade>

          <BlurFade delay={0.06} duration={0.6} offset={16}>
            <div className="card card-pad">
              <h3 className="card-title" style={{ marginBottom: "0.5rem" }}>
                Fault reason codes
              </h3>
              {detail.fault_breakdown.length === 0 ? (
                <p style={{ color: "var(--ink-3)", fontSize: "0.875rem" }}>
                  No fault-labelled detections in this window.
                </p>
              ) : (
                <div className="meter-list">
                  {detail.fault_breakdown.map((row) => (
                    <div key={row.reason_code} className="meter">
                      <div className="meter-head">
                        <span className="meter-name">{row.reason_code.replace(/_/g, " ")}</span>
                        <span className="meter-value">{row.count}</span>
                      </div>
                      <div className="meter-track">
                        <div
                          className="meter-fill"
                          style={{
                            width: `${Math.min(100, (row.count / Math.max(...detail.fault_breakdown.map((item) => item.count))) * 100)}%`,
                            height: "100%",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </BlurFade>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <h2 className="section-title">Recent detections</h2>
            <p className="section-note" style={{ marginTop: "0.2rem" }}>
              top 25 by anomaly score
            </p>
          </div>
          <Link href="/model" className="btn">
            How scores work
            <ArrowUpRight size={13} weight="bold" />
          </Link>
        </div>
        <BlurFade delay={0.02} duration={0.6} offset={16}>
          <div className="card-flat">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Sensor</th>
                    <th style={{ textAlign: "right" }}>Value</th>
                    <th style={{ textAlign: "right" }}>Score</th>
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
                        <td>{row.timestamp.replace("T", " ").slice(0, 16)}</td>
                        <td>{row.sensor_name.replace("_", " ")}</td>
                        <td style={{ textAlign: "right" }}>
                          {row.measured_value === null ? "NaN" : row.measured_value.toFixed(2)}
                        </td>
                        <td style={{ textAlign: "right" }}>{row.anomaly_score.toFixed(2)}</td>
                        <td className="cell-muted">{row.event_label ?? "—"}</td>
                        <td className="cell-muted">{row.reason_code?.replace(/_/g, " ") ?? "—"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </BlurFade>
      </section>
    </>
  );
}
