"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { EventRecord } from "@/lib/types";
import { VerdictBadge } from "@/components/badges";
import { BlurFade } from "@/components/ui/blur-fade";

type Filter = "ALL" | "FAULT" | "EXTREME";

export function EventTable({ events }: { events: EventRecord[] }) {
  const [filter, setFilter] = useState<Filter>("ALL");
  const [query, setQuery] = useState("");

  const counts = useMemo(
    () => ({
      ALL: events.length,
      FAULT: events.filter((event) => event.label === "FAULT").length,
      EXTREME: events.filter((event) => event.label === "EXTREME").length,
    }),
    [events],
  );

  const visible = useMemo(() => {
    const byLabel =
      filter === "ALL" ? events : events.filter((event) => event.label === filter);
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return byLabel;
    }
    return byLabel.filter(
      (event) =>
        event.station_id.toLowerCase().includes(needle) ||
        event.sensor_name.toLowerCase().includes(needle) ||
        event.reason_code.toLowerCase().includes(needle),
    );
  }, [events, filter, query]);

  return (
    <>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "0.75rem",
          flexWrap: "wrap",
          marginBottom: "0.75rem",
        }}
      >
        <div className="pill-tabs" role="tablist" aria-label="Filter by verdict">
          {(["ALL", "FAULT", "EXTREME"] as Filter[]).map((option) => (
            <button
              key={option}
              type="button"
              role="tab"
              aria-selected={filter === option}
              className="pill-tab"
              data-active={filter === option}
              onClick={() => setFilter(option)}
            >
              {option === "ALL" ? "All" : option.charAt(0) + option.slice(1).toLowerCase()}
              <span style={{ marginLeft: "0.35rem", color: "var(--ink-4)" }}>{counts[option]}</span>
            </button>
          ))}
        </div>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            fontSize: "0.8125rem",
            color: "var(--ink-3)",
          }}
        >
          <span className="sr-only" style={{ position: "absolute", left: "-9999px" }}>
            Filter by station, sensor or reason
          </span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Station, sensor or reason…"
            style={{
              border: "1px solid var(--hairline-strong)",
              borderRadius: "999px",
              padding: "0.4rem 0.75rem",
              fontSize: "0.8125rem",
              background: "var(--surface)",
              color: "var(--ink)",
              minWidth: "14rem",
              outline: "none",
            }}
          />
        </label>
      </div>

      <BlurFade delay={0.02} duration={0.6} offset={16}>
        <div className="card-flat">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Station</th>
                  <th>Sensor</th>
                  <th>Start</th>
                  <th style={{ textAlign: "right" }}>Hours</th>
                  <th>Verdict</th>
                  <th>Reason</th>
                  <th style={{ textAlign: "right" }}>Neighbour</th>
                  <th style={{ textAlign: "right" }}>Score</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{ color: "var(--ink-3)", padding: "2rem" }}>
                      No episodes match this filter.
                    </td>
                  </tr>
                ) : (
                  visible.map((event) => (
                    <tr key={event.event_id}>
                      <td className="cell-muted">{event.event_id}</td>
                      <td>
                        <Link href={`/stations/${event.station_id}`} className="row-link">
                          {event.station_id}
                        </Link>
                      </td>
                      <td>{event.sensor_name.replace("_", " ")}</td>
                      <td>{event.start.slice(0, 16).replace("T", " ")}</td>
                      <td style={{ textAlign: "right" }}>{event.duration_hours}</td>
                      <td>
                        <VerdictBadge label={event.label} />
                      </td>
                      <td className="cell-muted">{event.reason_code.replace(/_/g, " ")}</td>
                      <td style={{ textAlign: "right" }}>
                        {event.neighbour_agreement.toFixed(2)}
                      </td>
                      <td style={{ textAlign: "right" }}>{event.mean_anomaly_score.toFixed(2)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </BlurFade>
    </>
  );
}
