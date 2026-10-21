import Link from "next/link";
import { Suspense } from "react";
import { getEvents } from "@/lib/api";
import { EventRecord } from "@/lib/types";
import { TableSkeleton } from "@/components/skeletons";

function groupByReason(events: EventRecord[]) {
  const counts: Record<string, number> = {};
  for (const event of events) {
    counts[event.reason_code] = (counts[event.reason_code] ?? 0) + 1;
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1]);
}

async function EventBody() {
  let events: EventRecord[] = [];
  let error: string | null = null;

  try {
    const response = await getEvents(400);
    events = response.events;
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "unknown error";
  }

  const faultEvents = events.filter((event) => event.label === "FAULT");
  const extremeEvents = events.filter((event) => event.label === "EXTREME");
  const reasonCounts = groupByReason(events);

  return (
    <>
      <header className="page-head">
        <div>
          <h1 className="page-title">What the rule tree decided</h1>
          <p className="page-sub">
            Consecutive flagged hours are grouped into episodes. Each episode gets one verdict from
            three consistency signals: cross-sensor coherence, neighbour agreement, and physical
            plausibility.
          </p>
        </div>
        <div className="stamp">
          <div>{events.length} episodes</div>
          <div>{faultEvents.length} fault · {extremeEvents.length} extreme</div>
        </div>
      </header>

      {error ? (
        <div className="error-panel" style={{ marginTop: "1.5rem" }}>
          <h2 className="error-title">Could not load events</h2>
          <p className="code-line">{error}</p>
        </div>
      ) : (
        <>
          <section className="section">
            <div className="section-head">
              <h2 className="section-title">Verdict distribution</h2>
              <span className="section-note">by reason code</span>
            </div>
            <div className="panel">
              {reasonCounts.map(([reason, count]) => (
                <div key={reason} className="meter">
                  <div className="meter-head">
                    <span className="meter-name">{reason}</span>
                    <span className="mono">{count}</span>
                  </div>
                  <div className="meter-track">
                    <div
                      className="meter-fill"
                      style={{ width: `${(count / Math.max(events.length, 1)) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="section">
            <div className="section-head">
              <h2 className="section-title">Episodes</h2>
              <span className="section-note">most recent first</span>
            </div>
            <div className="panel-flush scroll-x">
              <table className="table">
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Station</th>
                    <th>Sensor</th>
                    <th>Start</th>
                    <th>Hours</th>
                    <th>Verdict</th>
                    <th>Reason</th>
                    <th>Neighbour</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr key={event.event_id}>
                      <td className="mono">{event.event_id}</td>
                      <td>
                        <Link href={`/stations/${event.station_id}`} className="row-link mono">
                          {event.station_id}
                        </Link>
                      </td>
                      <td className="mono">{event.sensor_name}</td>
                      <td className="mono">{event.start.slice(0, 16).replace("T", " ")}</td>
                      <td className="mono">{event.duration_hours}</td>
                      <td>
                        <span className="badge" data-label={event.label}>
                          {event.label.toLowerCase()}
                        </span>
                      </td>
                      <td className="mono" style={{ color: "var(--ink-3)" }}>
                        {event.reason_code}
                      </td>
                      <td className="mono">{event.neighbour_agreement.toFixed(2)}</td>
                      <td className="mono">{event.mean_anomaly_score.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}

export default function EventsPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={10} />}>
      <EventBody />
    </Suspense>
  );
}
