"use client";

import { useState } from "react";
import { SensorLineChart } from "@/components/charts";
import { StationSeries } from "@/lib/types";
import { VerdictBadge } from "@/components/badges";
import { BlurFade } from "@/components/ui/blur-fade";

const sensorLabels: Record<string, { label: string; unit: string }> = {
  temperature: { label: "Temperature", unit: "°C" },
  humidity: { label: "Humidity", unit: "%" },
  wind_speed: { label: "Wind speed", unit: "km/h" },
  pressure: { label: "Pressure", unit: "hPa" },
};

export function StationSeriesPanel({ series }: { series: StationSeries }) {
  const sensorNames = Object.keys(series.series);
  const [activeSensor, setActiveSensor] = useState(sensorNames[0] ?? "");
  const activeSeries = series.series[activeSensor];

  if (!activeSeries) {
    return (
      <div className="empty-state">
        <p>No series available for this station.</p>
      </div>
    );
  }

  const stride = Math.max(1, Math.floor(activeSeries.timestamps.length / 720));
  const sampled = activeSeries.timestamps
    .map((timestamp, index) => ({ timestamp, index }))
    .filter((_, index) => index % stride === 0);

  const timestamps = sampled.map((entry) => entry.timestamp);
  const values = sampled.map((entry) => activeSeries.values[entry.index]);
  const anomalies = sampled.map((entry) => activeSeries.is_anomaly[entry.index]);
  const baselineFlags = sampled.map((entry) => activeSeries.baseline_flag[entry.index]);
  const meta = sensorLabels[activeSensor] ?? { label: activeSensor, unit: "" };
  const sensorEvents = series.events.filter((event) => event.sensor_name === activeSensor);

  return (
    <>
      <BlurFade delay={0.02} duration={0.6} offset={16}>
        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">Readings and flags</h3>
              <p className="card-caption">
                {meta.label}
                {meta.unit ? ` · ${meta.unit}` : ""} · last {series.days} days
              </p>
            </div>
            <div className="pill-tabs" role="tablist" aria-label="Sensor selector">
              {sensorNames.map((sensor) => (
                <button
                  key={sensor}
                  type="button"
                  role="tab"
                  aria-selected={sensor === activeSensor}
                  className="pill-tab"
                  data-active={sensor === activeSensor}
                  onClick={() => setActiveSensor(sensor)}
                >
                  {sensorLabels[sensor]?.label.split(" ")[0] ?? sensor}
                </button>
              ))}
            </div>
          </div>
          <div style={{ padding: "0.5rem 0.75rem 1rem" }}>
            <SensorLineChart
              timestamps={timestamps}
              values={values}
              anomalies={anomalies}
              baselineFlags={baselineFlags}
              bands={series.events
                .filter((event) => event.sensor_name === activeSensor)
                .map((event) => ({ start: event.start, end: event.end, label: event.label }))}
              unit={meta.unit || undefined}
            />
          </div>
        </div>
      </BlurFade>

      {sensorEvents.length > 0 ? (
        <BlurFade delay={0.06} duration={0.6} offset={16}>
          <div className="card-flat">
            <div className="card-head">
              <div>
                <h3 className="card-title">{meta.label} episodes</h3>
                <p className="card-caption">
                  consecutive flagged hours grouped into episodes · last {series.days} days
                </p>
              </div>
              <span className="chip" data-tone="neutral">
                {sensorEvents.length} {sensorEvents.length === 1 ? "episode" : "episodes"}
              </span>
            </div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Sensor</th>
                    <th>Start</th>
                    <th>End</th>
                    <th>Verdict</th>
                    <th>Reason</th>
                    <th style={{ textAlign: "right" }}>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {sensorEvents
                    .slice(-12)
                    .reverse()
                    .map((event) => (
                      <tr key={event.event_id}>
                        <td className="cell-muted">{event.event_id}</td>
                        <td>{sensorLabels[event.sensor_name]?.label ?? event.sensor_name.replace("_", " ")}</td>
                        <td>{event.start.slice(0, 16).replace("T", " ")}</td>
                        <td>{event.end.slice(0, 16).replace("T", " ")}</td>
                        <td>
                          <VerdictBadge label={event.label} />
                        </td>
                        <td className="cell-muted">{event.reason_code}</td>
                        <td style={{ textAlign: "right" }}>{event.mean_anomaly_score.toFixed(2)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </BlurFade>
      ) : null}
    </>
  );
}
