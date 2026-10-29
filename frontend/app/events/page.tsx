import { getEvents } from "@/lib/api";
import { EventRecord } from "@/lib/types";
import { EventTable } from "@/components/event-table";
import { PageHead, Section, TickedNumber } from "@/components/page-parts";
import { TopBar } from "@/components/top-bar";
import { BlurFade } from "@/components/ui/blur-fade";

const reasonCopy: Record<string, string> = {
  bias: "The sensor reads a constant offset away from the truth.",
  drift: "The offset grows slowly over days.",
  stuck: "The sensor keeps reporting the same value.",
  spike: "Isolated readings jump far from their neighbours.",
  precision: "Readings are coarsely rounded and noisy.",
  dropout: "Readings are missing.",
  heat_wave: "Temperature rises while humidity and pressure fall across the station.",
  cold_snap: "Temperature drops while wind and humidity rise.",
  storm: "Wind rises sharply while pressure falls.",
  heavy_rain: "Humidity saturates while temperature dips.",
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
  const width = (count: number, peak: number) => Math.sqrt(count / peak) * 100;

  return (
    <>
      <TopBar />
      <PageHead
        size="large"
        title="What the model decided"
        description="Consecutive flagged hours on one sensor are grouped into episodes. Each episode takes the class the Random Forest predicted most often inside it."
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
            <BlurFade delay={0.02} duration={0.32} offset={14}>
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
            <BlurFade delay={0.06} duration={0.32} offset={14}>
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
            <BlurFade delay={0.1} duration={0.32} offset={14}>
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
            <BlurFade delay={0.14} duration={0.32} offset={14}>
              <div className="metric">
                <div className="metric-top">
                  <span className="metric-label">Distinct classes</span>
                </div>
                <div className="metric-value">
                  <TickedNumber value={reasonCounts.length} />
                </div>
                <div className="metric-foot">
                  <span>predicted by the model</span>
                </div>
              </div>
            </BlurFade>
          </div>

          <Section title="Verdict distribution" note="Which class the model predicted.">
            <div className="split">
              <BlurFade delay={0.02} duration={0.32} offset={16}>
                <div className="card card-pad">
                  <div className="meter-list">
                    {reasonCounts.map(([reason, count]) => {
                      const share = (count / Math.max(events.length, 1)) * 100;
                      const tone =
                        ["bias", "drift", "stuck", "spike", "precision", "dropout"].includes(reason)
                          ? "fault"
                          : ["heat_wave", "cold_snap", "storm", "heavy_rain"].includes(reason)
                            ? "extreme"
                            : undefined;
                      return (
                        <div key={reason} className="meter">
                          <div className="meter-head">
                            <span className="meter-name">{reason.replace(/_/g, " ")}</span>
                            <span className="meter-value">
                              <span className="meter-count">
                                {share < 0.1 && share > 0 ? "<0.1" : share.toFixed(1)}%
                              </span>
                              <span>{count}</span>
                            </span>
                          </div>
                          <div className="meter-track">
                            <div
                              className="meter-fill"
                              data-tone={tone}
                              style={{ width: `${width(count, maxReason)}%`, height: "100%" }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </BlurFade>

              <BlurFade delay={0.06} duration={0.32} offset={16}>
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
            note="Filter by verdict, or search a station, sensor or class."
          >
            <EventTable events={events} />
          </Section>
        </>
      )}
    </>
  );
}
