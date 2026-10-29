import Link from "next/link";
import { ArrowUpRight } from "@phosphor-icons/react/dist/ssr";
import { getMetrics, getStations } from "@/lib/api";
import { MetricsSummary, StationHealth } from "@/lib/types";
import { StatusBadge } from "@/components/badges";
import { PageHead, Section } from "@/components/page-parts";
import { TopBar } from "@/components/top-bar";
import { BlurFade } from "@/components/ui/blur-fade";

const statusRank = (status: StationHealth["status"]) =>
  ({ FAULT: 0, EXTREME_EVENT: 1, WATCH: 2, HEALTHY: 3 })[status] ?? 4;

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
      <>
        <TopBar />
        <PageHead title="Stations" description="Station data could not be loaded." />
        <div className="error-panel">
          <h2 className="error-title">Station data unavailable</h2>
          <p className="code-line">{error}</p>
        </div>
      </>
    );
  }

  const sorted = [...stations].sort(
    (a, b) =>
      statusRank(a.status) - statusRank(b.status) || a.station_id.localeCompare(b.station_id),
  );

  return (
    <>
      <TopBar />
      <PageHead
        size="large"
        title="Station integrity"
        description="Every site is judged on its trailing 30 days: faults first, then genuine extremes, then elevated flag density. Open a station for the hour-by-hour trace."
        aside={
          <>
            <span>{stations.length} stations</span>
            <span>{metrics ? metrics.label_counts.total_readings.toLocaleString() : "—"} readings</span>
          </>
        }
      />

      <Section title="Fleet status" note="Sorted by severity, faults first.">
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
                    <th style={{ textAlign: "right" }}>Events</th>
                    <th style={{ textAlign: "right" }}>Accuracy</th>
                    <th>Last reading</th>
                    <th aria-label="Open" />
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((station) => {
                    const stationMetrics = metrics?.per_station[station.station_id];
                    return (
                      <tr key={station.station_id}>
                        <td>
                          <Link href={`/stations/${station.station_id}`} className="station-cell">
                            <span className="station-id">{station.station_id}</span>
                            <span className="station-name">
                              <span className="cell-strong">{station.station_name}</span>
                              <small>
                                {station.latitude.toFixed(2)}, {station.longitude.toFixed(2)}
                              </small>
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
                        <td style={{ textAlign: "right" }}>
                          {station.anomalous_percent.toFixed(2)}%
                        </td>
                        <td style={{ textAlign: "right" }}>{station.total_events}</td>
                        <td style={{ textAlign: "right" }}>
                          {stationMetrics
                            ? `${(stationMetrics.accuracy * 100).toFixed(1)}%`
                            : "—"}
                        </td>
                        <td className="cell-muted">
                          {new Date(station.last_reading_at).toLocaleDateString("en-GB", {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                          })}
                        </td>
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
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </BlurFade>
      </Section>

      <Section title="How status is decided" note="A strict precedence order, not a score.">
        <div className="cols-2">
          {[
            {
              status: "FAULT" as const,
              rule: "any fault-labelled event in the trailing window",
            },
            {
              status: "EXTREME_EVENT" as const,
              rule: "no faults, but a genuine extreme-labelled event",
            },
            {
              status: "WATCH" as const,
              rule: "no events, but anomalous share above 5%",
            },
            {
              status: "HEALTHY" as const,
              rule: "none of the above",
            },
          ].map((item, index) => (
            <BlurFade key={item.status} delay={index * 0.05} duration={0.32} offset={12}>
              <div className="card card-pad">
                <StatusBadge status={item.status} />
                <p style={{ marginTop: "0.6rem", fontSize: "0.875rem", color: "var(--ink-2)" }}>
                  {item.rule}.
                </p>
              </div>
            </BlurFade>
          ))}
        </div>
      </Section>
    </>
  );
}
