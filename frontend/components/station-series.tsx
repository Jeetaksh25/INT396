"use client";

import { useState } from "react";
import { SensorLineChart } from "@/components/charts";
import { StationSeries } from "@/lib/types";

const sensorLabels: Record<string, string> = {
  temperature: "Temperature · °C",
  humidity: "Humidity · %",
  wind_speed: "Wind speed · km/h",
  pressure: "Pressure · hPa",
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

  const sampled = activeSeries.timestamps.map((timestamp, index) => ({ timestamp, index }));
  const stride = Math.max(1, Math.floor(sampled.length / 720));
  const thinned = sampled.filter((_, index) => index % stride === 0);
  const timestamps = thinned.map((entry) => entry.timestamp);
  const values = thinned.map((entry) => activeSeries.values[entry.index]);
  const anomalies = thinned.map((entry) => activeSeries.is_anomaly[entry.index]);
  const baselineFlags = thinned.map((entry) => activeSeries.baseline_flag[entry.index]);

  return (
    <section className="section">
      <div className="section-head">
        <h2 className="section-title">Readings and flags</h2>
        <div className="toolbar" role="tablist" aria-label="Sensor selector">
          {sensorNames.map((sensor) => (
            <button
              key={sensor}
              type="button"
              role="tab"
              aria-selected={sensor === activeSensor}
              className="chip"
              data-active={sensor === activeSensor}
              onClick={() => setActiveSensor(sensor)}
            >
              {sensor}
            </button>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="legend" style={{ marginBottom: "0.75rem" }}>
          <span className="legend-item">
            <span className="swatch" style={{ background: "oklch(72% 0.05 250)" }} />
            {sensorLabels[activeSensor] ?? activeSensor}
          </span>
          <span className="legend-item">
            <span className="swatch" style={{ background: "oklch(68% 0.19 22)" }} />
            consensus flag
          </span>
          <span className="legend-item">
            <span className="swatch" style={{ background: "oklch(84% 0.14 92)" }} />
            range-check flag
          </span>
        </div>
        <SensorLineChart
          timestamps={timestamps}
          values={values}
          anomalies={anomalies}
          baselineFlags={baselineFlags}
        />
      </div>

      {series.events.length > 0 ? (
        <div className="panel-flush scroll-x">
          <table className="table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Sensor</th>
                <th>Start</th>
                <th>End</th>
                <th>Verdict</th>
                <th>Reason</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {series.events.slice(-12).reverse().map((event) => (
                <tr key={event.event_id}>
                  <td className="mono">{event.event_id}</td>
                  <td className="mono">{event.sensor_name}</td>
                  <td className="mono">{event.start.slice(0, 16).replace("T", " ")}</td>
                  <td className="mono">{event.end.slice(0, 16).replace("T", " ")}</td>
                  <td>
                    <span className="badge" data-label={event.label}>
                      {event.label.toLowerCase()}
                    </span>
                  </td>
                  <td className="mono" style={{ color: "var(--ink-3)" }}>
                    {event.reason_code}
                  </td>
                  <td className="mono">{event.mean_anomaly_score.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
