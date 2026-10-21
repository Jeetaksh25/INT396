import { getEvents } from "@/lib/api";
import { EventRecord } from "@/lib/types";
import { EventTable } from "@/components/event-table";
import { PageHead, Section, TickedNumber } from "@/components/page-parts";
import { TopBar } from "@/components/top-bar";
import { BlurFade } from "@/components/ui/blur-fade";

const reasonCopy: Record<string, string> = {
  physics_inconsistent: "A hard physical rule was violated, so the instrument cannot be reporting weather.",
  isolated_sensor: "One sensor deviates while its neighbours at the same station stay normal.",
  coherent_multi_sensor: "Several sensors move together, the signature of a real weather event.",
  coherent_regional: "Sensors move together and nearby stations agree, so the event is regional.",
  sustained_regime: "The deviation persists at a stable level long enough to be a regime change.",
  isolated_or_erratic: "No coherence signal survived, so the episode defaults to a fault.",
};

export default async function EventsPage() {
  let events: EventRecord[] = [];
  let error: string | null = null;

  try {
    const response = await getEvents(1000);
    events = response.events;
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "unknown error";
  }

  const faultEvents = events.filter((event) => event.label === "FAULT");
  const extremeEvents = events.filter((event) => event.label === "EXTREME");
  const reasonCounts = Object.entries(
    events.reduce<Record<string, number>>((accumulator, event) => {
      accumulator[event.reason_code] = (accumulator[event.reason_code] ?? 0) + 1;
      return accumulator;
    }, {}),
  ).sort((a, b) => b[1] - a[1]);
  const maxReason = Math.max(...reasonCounts.map((entry) => entry[1]), 1);

  return (
    <>
      <TopBar />
      <PageHead
        size="large"
        title="What the rule tree decided"
        description="Consecutive flagged hours are grouped into episodes. Each episode gets one verdict from three consistency signals: cross-sensor coherence, neighbour agreement, and physical plausibility."
        aside={
          <>
            <span>{events.length} episodes</span>
            <span>
              {faultEvents.length} fault · {extremeEvents.length} extreme
            </span>
          </>
        }
      />

      {error ? (
        <div className="error-panel">
          <h2 className="error-title">Could not load events</h2>
          <p className="code-line">{error}</p>
        </div>
      ) : (
        <>
          <div className="metric-grid">
            <BlurFade delay={0.02} duration={0.6} offset={14}>
              <div className="metric">
                <div className="metric-top">
                  <span className="metric-label">Episodes grouped</span>
                </div>
                <div className="metric-value">
                  <TickedNumber value={events.length} />
                </div>
                <div className="metric-foot">
                  <span>from consecutive flagged hours</span>
                </div>
              </div>
            </BlurFade>
            <BlurFade delay={0.06} duration={0.6} offset={14}>
              <div className="metric">
                <div className="metric-top">
                  <span className="metric-label">Fault verdicts</span>
                </div>
                <div className="metric-value">
                  <TickedNumber value={faultEvents.length} />
                </div>
                <div className="metric-foot">
                  <span>
                    {((faultEvents.length / Math.max(events.length, 1)) * 100).toFixed(1)}% of
                    episodes
                  </span>
                </div>
              </div>
            </BlurFade>
            <BlurFade delay={0.1} duration={0.6} offset={14}>
              <div className="metric">
                <div className="metric-top">
                  <span className="metric-label">Extreme verdicts</span>
                </div>
                <div className="metric-value">
                  <TickedNumber value={extremeEvents.length} />
                </div>
                <div className="metric-foot">
                  <span>
                    {((extremeEvents.length / Math.max(events.length, 1)) * 100).toFixed(1)}% of
                    episodes
                  </span>
                </div>
              </div>
            </BlurFade>
            <BlurFade delay={0.14} duration={0.6} offset={14}>
              <div className="metric">
                <div className="metric-top">
                  <span className="metric-label">Distinct reason codes</span>
                </div>
                <div className="metric-value">
                  <TickedNumber value={reasonCounts.length} />
                </div>
                <div className="metric-foot">
                  <span>in the rule tree</span>
                </div>
              </div>
            </BlurFade>
          </div>

          <Section title="Verdict distribution" note="Which branch of the rule tree fired.">
            <div className="split">
              <BlurFade delay={0.02} duration={0.6} offset={16}>
                <div className="card card-pad">
                  <div className="meter-list">
                    {reasonCounts.map(([reason, count]) => (
                      <div key={reason} className="meter">
                        <div className="meter-head">
                          <span className="meter-name">{reason.replace(/_/g, " ")}</span>
                          <span className="meter-value">{count}</span>
                        </div>
                        <div className="meter-track">
                          <div
                            className="meter-fill"
                            style={{ width: `${(count / maxReason) * 100}%`, height: "100%" }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </BlurFade>

              <BlurFade delay={0.06} duration={0.6} offset={16}>
                <div className="card card-pad">
                  <h3 className="card-title" style={{ marginBottom: "0.6rem" }}>
                    What each code means
                  </h3>
                  <div className="def-list">
                    {reasonCounts.map(([reason]) => (
                      <div className="def-row" key={reason} style={{ display: "block" }}>
                        <div className="cell-strong" style={{ marginBottom: "0.15rem" }}>
                          {reason.replace(/_/g, " ")}
                        </div>
                        <div style={{ color: "var(--ink-3)", fontSize: "0.8125rem", lineHeight: 1.5 }}>
                          {reasonCopy[reason] ?? "Rule-tree branch."}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </BlurFade>
            </div>
          </Section>

          <Section
            title="Episodes"
            note="Filter by verdict, or search a station, sensor or reason code."
          >
            <EventTable events={events} />
          </Section>
        </>
      )}
    </>
  );
}
