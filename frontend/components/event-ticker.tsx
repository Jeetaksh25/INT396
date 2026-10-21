"use client";

import { useEffect, useState } from "react";
import { getEvents } from "@/lib/api";
import { EventRecord } from "@/lib/types";

export function EventTicker() {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getEvents(6)
      .then((response) => {
        if (!cancelled) {
          setEvents(response.events);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed || events.length === 0) {
    return null;
  }

  return (
    <section className="section">
      <div className="section-head">
        <h2 className="section-title">Latest verdicts</h2>
        <span className="section-note">from the rule tree</span>
      </div>
      <div className="panel-flush scroll-x">
        <table className="table">
          <thead>
            <tr>
              <th>Station</th>
              <th>Sensor</th>
              <th>Window</th>
              <th>Hours</th>
              <th>Verdict</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.event_id}>
                <td className="mono">{event.station_id}</td>
                <td className="mono">{event.sensor_name}</td>
                <td className="mono">{event.start.slice(0, 13).replace("T", " ")}</td>
                <td className="mono">{event.duration_hours}</td>
                <td>
                  <span className="badge" data-label={event.label}>
                    {event.label.toLowerCase()}
                  </span>
                </td>
                <td className="mono" style={{ color: "var(--ink-3)" }}>
                  {event.reason_code}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
