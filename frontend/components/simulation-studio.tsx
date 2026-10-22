"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowClockwise,
  ArrowRight,
  Gauge,
  Pause,
  Play,
  Sparkle,
} from "@phosphor-icons/react";
import type { SimDecision, SimRecord, SimResult } from "@/lib/simulation-types";
import { NumberTicker } from "@/components/ui/number-ticker";

const STEP_MS = 132;

const LANES: {
  key: SimDecision;
  label: string;
  caption: string;
  token: string;
}[] = [
  { key: "FAULT", label: "Fault", caption: "single sensor, physics broken", token: "fault" },
  { key: "EXTREME", label: "Extreme", caption: "coherent, regional weather", token: "extreme" },
  { key: "HEALTHY", label: "Healthy", caption: "within normal behaviour", token: "healthy" },
];

const DETECTORS = ["K", "D", "P", "I", "L"];

const PHASES = [
  { key: "generate", label: "Generate", detail: "inject faults + weather" },
  { key: "features", label: "Features", detail: "11 columns per reading" },
  { key: "detect", label: "Vote", detail: "5 detectors, 3 of 5 wins" },
  { key: "stream", label: "Classify", detail: "fault vs extreme vs clean" },
];

const SENSOR_LABEL: Record<string, string> = {
  temperature: "Temperature",
  humidity: "Humidity",
  wind_speed: "Wind speed",
  pressure: "Pressure",
};

const REASON_LABEL: Record<string, string> = {
  physics_inconsistent: "physics break",
  isolated_sensor: "isolated sensor",
  isolated_or_erratic: "erratic, isolated",
  coherent_regional: "coherent + regional",
  coherent_multi_sensor: "coherent across sensors",
};

type Phase = "idle" | "generating" | "streaming" | "done";

interface Ghost {
  id: number;
  x: number;
  y: number;
  dx: number;
  dy: number;
  record: SimRecord;
  lane: SimDecision;
}

function formatTime(value: string) {
  const date = new Date(value);
  return `${date.getDate()} ${date.toLocaleString("en-US", { month: "short" })} · ${String(
    date.getHours(),
  ).padStart(2, "0")}:00`;
}

export function SimulationStudio() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<SimResult | null>(null);
  const [cursor, setCursor] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ghosts, setGhosts] = useState<Ghost[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [runNumber, setRunNumber] = useState(0);
  const [serverPhase, setServerPhase] = useState<string>("generate");
  const [serverFraction, setServerFraction] = useState(0);
  const [profile, setProfile] = useState<string>("balanced");

  const incomingRef = useRef<HTMLDivElement | null>(null);
  const laneRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const ghostId = useRef(0);
  const startedAt = useRef<number>(0);

  const records = result?.records ?? [];
  const active = records[cursor];

  const committed = useMemo(() => {
    if (!result) return [];
    return result.records.slice(0, cursor);
  }, [result, cursor]);

  const laneRecords = useMemo(() => {
    const buckets: Record<string, SimRecord[]> = { FAULT: [], EXTREME: [], HEALTHY: [] };
    for (const record of committed) {
      buckets[record.decision].push(record);
    }
    return buckets;
  }, [committed]);

  const runSimulation = useCallback(async () => {
    setPhase("generating");
    setResult(null);
    setCursor(0);
    setError(null);
    setPaused(false);
    setElapsed(0);
    startedAt.current = Date.now();

    const seed = Math.floor(Math.random() * 900000) + 1000;
    setServerPhase("generate");
    setServerFraction(0);

    try {
      const response = await fetch(
        `/api/simulation/events?seed=${seed}&profile=${profile}`,
      );
      if (!response.ok || !response.body) {
        throw new Error(`request failed (${response.status})`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let settled: SimResult | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const line = frame.split("\n").find((entry) => entry.startsWith("data:"));
          if (!line) continue;
          const payload = JSON.parse(line.slice(5).trim()) as {
            phase: string;
            fraction: number;
            detail?: string;
            result?: SimResult;
          };

          if (payload.phase === "complete" && payload.result) {
            settled = payload.result;
          } else if (payload.phase === "failed") {
            throw new Error(payload.detail ?? "simulation failed");
          } else {
            setServerPhase(payload.phase);
            setServerFraction(payload.fraction);
          }
        }
      }

      if (!settled) {
        throw new Error("simulation returned no result");
      }
      if (!settled.records?.length) {
        throw new Error("no readings returned");
      }
      setResult(settled);
      setRunNumber((value) => value + 1);
      setPhase("streaming");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "unknown error");
      setPhase("idle");
    }
  }, [profile]);

  const flyGhost = useCallback((record: SimRecord) => {
    const source = incomingRef.current?.getBoundingClientRect();
    const target = laneRefs.current[record.decision]?.getBoundingClientRect();
    if (!source || !target) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    ghostId.current += 1;
    const id = ghostId.current;
    setGhosts((current) => [
      ...current.slice(-6),
      {
        id,
        x: source.left,
        y: source.top,
        dx: target.left + 18 - source.left,
        dy: target.top + 54 - source.top,
        record,
        lane: record.decision,
      },
    ]);
    window.setTimeout(() => {
      setGhosts((current) => current.filter((ghost) => ghost.id !== id));
    }, 560);
  }, []);

  useEffect(() => {
    if (phase !== "streaming" || !result) return;
    if (cursor >= result.records.length) {
      setPhase("done");
      return;
    }
    if (paused) return;

    const timer = window.setTimeout(() => {
      flyGhost(result.records[cursor]);
      setCursor((value) => value + 1);
    }, STEP_MS / speed);

    return () => window.clearTimeout(timer);
  }, [phase, cursor, result, speed, paused, flyGhost]);

  useEffect(() => {
    if (phase !== "generating") return;
    const timer = window.setInterval(() => {
      setElapsed(Math.round((Date.now() - startedAt.current) / 100) / 10);
    }, 100);
    return () => window.clearInterval(timer);
  }, [phase]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "r" && !event.metaKey && !event.ctrlKey) {
        runSimulation();
      }
      if (event.key === " ") {
        event.preventDefault();
        setPaused((value) => !value);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [runSimulation]);

  const progress =
    phase === "done" ? 1 : records.length ? cursor / records.length : 0;

  const activePhaseIndex =
    phase === "generating"
      ? serverPhase === "generate" && serverFraction < 0.5
        ? 0
        : serverPhase === "features" || (serverPhase === "generate" && serverFraction >= 0.5)
          ? 1
          : 2
      : phase === "streaming" || phase === "done"
        ? 3
        : -1;


  const stats = result?.stream;

  return (
    <div className="sim">
      <div className="sim-console">
        <div className="sim-console-main">
          <button
            type="button"
            className="btn btn-primary sim-run"
            onClick={runSimulation}
            disabled={phase === "generating"}
            data-state={phase}
          >
            {phase === "generating" ? (
              <>
                <ArrowClockwise size={17} className="sim-spin" aria-hidden="true" />
                Building dataset
              </>
            ) : phase === "streaming" || phase === "done" ? (
              <>
                <ArrowClockwise size={17} aria-hidden="true" />
                Run another seed
              </>
            ) : (
              <>
                <Sparkle size={17} weight="fill" aria-hidden="true" />
                Generate dataset
              </>
            )}
          </button>

          <div className="sim-console-meta">
            {result ? (
              <>
                <span className="sim-meta-item">
                  seed <b className="num">{result.seed}</b>
                </span>
                <span className="sim-meta-item">
                  window{" "}
                  <b className="num">
                    {result.window.start.slice(0, 10)} → {result.window.end.slice(0, 10)}
                  </b>
                </span>
                <span className="sim-meta-item">
                  <b className="num">{result.counts.readings.toLocaleString()}</b> readings
                </span>
                <span className="sim-meta-item">
                  <b className="num">{result.counts.fault_episodes}</b> fault ·{" "}
                  <b className="num">{result.counts.extreme_episodes}</b> extreme episodes
                </span>
              </>
            ) : (
              <span className="sim-meta-item">
                Generates a fresh window, injects faults, runs the full model.
              </span>
            )}
          </div>
        </div>

        <div className="sim-console-side">
          {phase === "streaming" || phase === "done" ? (
            <button
              type="button"
              className="btn sim-ghost-btn"
              onClick={() => setPaused((value) => !value)}
            >
              {paused ? <Play size={15} weight="fill" /> : <Pause size={15} weight="fill" />}
              {paused ? "Resume" : "Pause"}
            </button>
          ) : null}
          <div className="sim-profile" role="group" aria-label="Operating point">
            {[
              { key: "high_precision", label: "Precise" },
              { key: "balanced", label: "Balanced" },
              { key: "high_recall", label: "Sensitive" },
            ].map((item) => (
              <button
                key={item.key}
                type="button"
                className="sim-speed-btn"
                data-active={profile === item.key}
                onClick={() => setProfile(item.key)}
                title={
                  item.key === "high_precision"
                    ? "Fewer alarms, higher confidence"
                    : item.key === "high_recall"
                      ? "Catches more, more false alarms"
                      : "Calibrated balance of the two"
                }
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="sim-speed" role="group" aria-label="Playback speed">
            {[1, 2, 4].map((value) => (
              <button
                key={value}
                type="button"
                className="sim-speed-btn"
                data-active={speed === value}
                onClick={() => setSpeed(value)}
              >
                {value}×
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="sim-phases" data-active={activePhaseIndex}>
        {PHASES.map((item, index) => (
          <div
            key={item.key}
            className="sim-phase"
            data-state={
              activePhaseIndex > index || phase === "done"
                ? "done"
                : activePhaseIndex === index
                  ? "active"
                  : "idle"
            }
          >
            <span className="sim-phase-dot" aria-hidden="true" />
            <span className="sim-phase-copy">
              <span className="sim-phase-label">{item.label}</span>
              <span className="sim-phase-detail">{item.detail}</span>
            </span>
          </div>
        ))}
      </div>

      {error ? (
        <div className="sim-error">
          <b>Simulation failed.</b> {error}. Check the backend on port 8000.
        </div>
      ) : null}

      {phase === "generating" ? (
        <GeneratingWall
          elapsed={elapsed}
          fraction={serverFraction}
          phase={serverPhase}
        />
      ) : null}

      {phase === "idle" ? <IdlePanel onRun={runSimulation} /> : null}

      {phase !== "idle" && phase !== "generating" ? (
        <div className="sim-stage">
          <div className="sim-incoming">
            <div className="sim-incoming-head">
                <span className="sim-eyebrow">
                {phase === "done" ? "Stream complete" : "Incoming reading"}
              </span>
              <span className="sim-counter num">
                {Math.min(cursor + (phase === "done" ? 0 : 1), records.length)} / {records.length}
              </span>
            </div>

            <div className="sim-progress">
              <span className="sim-progress-fill" style={{ width: `${progress * 100}%` }} />
            </div>

            {active && phase !== "done" ? (
              <div className="sim-reading" ref={incomingRef} key={`${runNumber}-${cursor}`}>
                <div className="sim-reading-top">
                  <span className="sim-reading-station">
                    {active.station_id} · {active.station_name}
                  </span>
                  <span className="sim-reading-time num">{formatTime(active.timestamp)}</span>
                </div>
                <div className="sim-reading-value">
                  <span className="num">
                    {active.measured_value === null
                      ? "—"
                      : active.measured_value.toFixed(1)}
                  </span>
                  <span className="sim-reading-unit">{active.unit}</span>
                </div>
                <div className="sim-reading-sensor">{SENSOR_LABEL[active.sensor_name]}</div>
                <div className="sim-votes">
                  {active.votes.map((vote, index) => (
                    <span
                      key={index}
                      className="sim-vote"
                      data-on={vote === 1}
                      data-delay={index}
                      title={`${["k-means", "dbscan", "pca", "isolation forest", "lof"][index]}: ${
                        vote ? "anomaly" : "normal"
                      }`}
                    >
                      {DETECTORS[index]}
                    </span>
                  ))}
                  <span className="sim-vote-count num">{active.vote_count}/5</span>
                </div>
              </div>
            ) : (
              <div className="sim-reading sim-reading-done">
                <div className="sim-reading-top">
                  <span className="sim-reading-station">All readings classified</span>
                </div>
                <p className="sim-reading-note">
                  {stats
                    ? `${stats.correct} of ${stats.total} sampled readings landed in the right lane.`
                    : "Finished."}
                </p>
              </div>
            )}
          </div>

          <div className="sim-lanes">
            {LANES.map((lane) => {
              const bucket = laneRecords[lane.key] ?? [];
              const recent = bucket.slice(-5).reverse();
              const count = bucket.length;
              return (
                <div key={lane.key} className="sim-lane" data-token={lane.token}>
                  <div className="sim-lane-head">
                    <div>
                      <span className="sim-lane-label">{lane.label}</span>
                      <span className="sim-lane-caption">{lane.caption}</span>
                    </div>
                    <span className="sim-lane-count num">
                      <NumberTicker value={count} decimalPlaces={0} animateOnView={false} />
                    </span>
                  </div>
                  <div
                    className="sim-lane-body"
                    ref={(node) => {
                      laneRefs.current[lane.key] = node;
                    }}
                  >
                    {recent.length === 0 ? (
                      <span className="sim-lane-empty">waiting</span>
                    ) : (
                      recent.map((record) => (
                        <div
                          key={`${record.timestamp}-${record.sensor_name}-${record.station_id}`}
                          className="sim-chip"
                          data-correct={record.correct}
                          title={`${record.station_name} · ${record.sensor_name} · actually ${record.truth}`}
                        >
                          <span className="sim-chip-station">{record.station_id}</span>
                          <span className="sim-chip-sensor">
                            {SENSOR_LABEL[record.sensor_name] ?? record.sensor_name}
                          </span>
                          <span className="sim-chip-value num">
                            {record.measured_value === null
                              ? "—"
                              : record.measured_value.toFixed(0)}
                          </span>
                          <span className="sim-chip-mark" aria-hidden="true" />
                        </div>
                      ))
                    )}
                  </div>
                  <div className="sim-lane-foot">
                    <span>
                      {bucket.filter((record) => record.correct).length}/{bucket.length} correct
                    </span>
                    {bucket.filter((record) => !record.correct).length ? (
                      <span className="sim-lane-wrong">
                        <i aria-hidden="true" />
                        {bucket.filter((record) => !record.correct).length} misplaced
                      </span>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {phase === "done" && result ? <RunReport result={result} /> : null}

      <div className="sim-ghost-layer" aria-hidden="true">
        {ghosts.map((ghost) => (
          <div
            key={ghost.id}
            className="sim-ghost"
            data-token={LANES.find((lane) => lane.key === ghost.lane)?.token}
            style={{
              left: ghost.x,
              top: ghost.y,
              transform: `translate3d(${ghost.dx}px, ${ghost.dy}px, 0) scale(0.62)`,
            }}
          >
            <span className="num">
              {ghost.record.measured_value === null
                ? "—"
                : ghost.record.measured_value.toFixed(0)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function IdlePanel({ onRun }: { onRun: () => void }) {
  return (
    <div className="sim-idle">
      <div className="sim-idle-copy">
        <span className="sim-eyebrow">Ready</span>
        <h2 className="sim-idle-title">One click runs the whole pipeline.</h2>
        <p className="sim-idle-body">
          A random window is cut from the clean year, weather extremes and sensor faults are
          injected, eleven features are built per reading, five detectors vote, and the rule tree
          decides fault or extreme. Then every reading is replayed into its lane.
        </p>
        <ol className="sim-idle-steps">
          <li>
            <span className="num">01</span> Cut a random 21-day window
          </li>
          <li>
            <span className="num">02</span> Inject 18 fault and 8 extreme episodes
          </li>
          <li>
            <span className="num">03</span> Score against the trained reference bank
          </li>
          <li>
            <span className="num">04</span> Replay readings into lanes with accuracy
          </li>
        </ol>
        <button type="button" className="btn sim-idle-cta" onClick={onRun}>
          Start the run
          <ArrowRight size={15} weight="bold" aria-hidden="true" />
        </button>
      </div>
      <div className="sim-idle-visual" aria-hidden="true">
        <div className="sim-preview">
          <span className="sim-preview-in">reading</span>
          <span className="sim-preview-arrow" />
          <span className="sim-preview-votes">
            <i data-on="true" />
            <i data-on="true" />
            <i data-on="true" />
            <i />
            <i />
          </span>
          <span className="sim-preview-arrow" />
          <span className="sim-preview-lanes">
            <i data-token="fault" />
            <i data-token="extreme" />
            <i data-token="healthy" />
          </span>
        </div>
        <span className="sim-preview-caption">one reading → five votes → one lane</span>
      </div>
    </div>
  );
}

function GeneratingWall({
  elapsed,
  fraction,
  phase,
}: {
  elapsed: number;
  fraction: number;
  phase: string;
}) {
  const stations = ["DEL", "BOM", "MAA", "HYD", "JAI", "CCU", "BLR", "SLM"];
  const sensors = ["temp", "hum", "wind", "pres"];

  return (
    <div className="sim-wall-wrap">
      <div className="sim-wall-head">
        <span className="sim-eyebrow">
          <Gauge size={14} weight="bold" aria-hidden="true" /> Generating dataset
        </span>
        <span className="sim-wall-clock num">
          {Math.round(fraction * 100)}% · {elapsed.toFixed(1)}s
        </span>
      </div>
      <div className="sim-wall">
        {stations.map((station, rowIndex) => (
          <div key={station} className="sim-wall-row">
            <span className="sim-wall-station">{station}</span>
            {sensors.map((sensor, columnIndex) => (
              <span
                key={sensor}
                className="sim-wall-cell"
                style={{ animationDelay: `${(rowIndex * 4 + columnIndex) * 34}ms` }}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="sim-wall-progress">
        <span style={{ width: `${Math.max(3, fraction * 100)}%` }} />
      </div>
      <p className="sim-wall-note">
        {phase === "train"
          ? "Fitting the reference bank once: k-means, DBSCAN, PCA, isolation forest and LOF on the clean year."
          : "Injecting bias, drift, stuck, spike, precision and dropout faults; then laying heat waves, cold snaps, storms and heavy rain over the same window."}
      </p>
    </div>
  );
}

function RunReport({ result }: { result: SimResult }) {
  const { stream, detector, baseline, delta } = result;

  const cards = [
    {
      label: "Fault detection rate",
      value: detector.fault_detection_rate * 100,
      decimals: 1,
      suffix: "%",
      caption: `${result.confusion.fault.flagged} of ${result.confusion.fault.total} fault readings caught`,
    },
    {
      label: "F1 on fault class",
      value: detector.f1,
      decimals: 3,
      suffix: "",
      caption: `${delta.f1 > 0 ? "+" : ""}${(delta.f1 * 100).toFixed(1)}pp vs range check`,
    },
    {
      label: "Precision",
      value: detector.precision * 100,
      decimals: 1,
      suffix: "%",
      caption: `range check: ${(baseline.precision * 100).toFixed(0)}% precision but ${(baseline.recall * 100).toFixed(0)}% recall`,
    },
    {
      label: "False alarms",
      value: detector.false_positive_rate_clean * 100,
      decimals: 2,
      suffix: "%",
      caption: `${result.confusion.clean.flagged} of ${result.confusion.clean.total} clean readings`,
    },
    {
      label: "Macro F1",
      value: result.macro_f1,
      decimals: 3,
      suffix: "",
      caption: "mean of fault, extreme and clean",
    },
  ];

  const truthRows = [
    { key: "fault" as const, label: "Fault", token: "fault" },
    { key: "extreme" as const, label: "Extreme", token: "extreme" },
    { key: "clean" as const, label: "Clean", token: "healthy" },
  ];

  return (
    <section className="sim-report">
      <div className="sim-report-head">
        <h2 className="section-title">Run report</h2>
        <span className="sim-report-note">
          seed <b className="num">{result.seed}</b> · {result.counts.readings.toLocaleString()}{" "}
          readings · {result.counts.hours} hours · {result.timing.total_seconds}s ·{" "}
          <b>{result.operating_point.replace("_", " ")}</b>
        </span>
      </div>

      <p className="sim-report-lede">
        Computed on all {result.counts.readings.toLocaleString()} readings in the window, not on
        the replay sample. Read fault detection rate and F1 first — plain accuracy is{" "}
        <b>{(result.window_accuracy * 100).toFixed(1)}%</b> here, but it is flattered by the{" "}
        {(100 * (result.counts.clean_readings / result.counts.readings)).toFixed(0)}% of readings
        that are clean, so it says little about the detector.
      </p>

      <div className="metric-grid sim-metric-grid">
        {cards.map((card) => (
          <div key={card.label} className="metric">
            <div className="metric-top">
              <span className="metric-label">{card.label}</span>
            </div>
            <div className="metric-value">
              <NumberTicker
                value={card.value}
                decimalPlaces={card.decimals}
                className="num"
                animateOnView={false}
              />
              {card.suffix}
            </div>
            <div className="metric-foot">
              <span>{card.caption}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="sim-report-grid">
        <div className="card card-pad">
          <h3 className="card-title">Where the replay landed</h3>
          <p className="card-caption">
            Replay shares: 60% clean / 22% fault / 18% extreme, so every lane stays visible.
            Window prevalence is {(100 * (result.counts.clean_readings / result.counts.readings)).toFixed(0)}%
            clean — the real rates are in the cards above.
          </p>
          <div className="sim-truth-list">
            {truthRows.map((row) => {
              const block = stream.by_truth[row.key];
              const share = block.total ? (block.correct / block.total) * 100 : 0;
              return (
                <div key={row.key} className="sim-truth" data-token={row.token}>
                  <div className="sim-truth-head">
                    <span>{row.label}</span>
                    <span className="num">
                      {block.correct}/{block.total}
                    </span>
                  </div>
                  <div className="sim-truth-track">
                    <span className="sim-truth-fill" style={{ width: `${share}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="card card-pad">
          <h3 className="card-title">Recall by class</h3>
          <p className="card-caption">Whole window, straight from the detector.</p>
          <div className="sim-truth-list">
            {(["fault", "extreme", "clean"] as const).map((key) => {
              const block = result.per_class[key];
              const token = key === "fault" ? "fault" : key === "extreme" ? "extreme" : "healthy";
              return (
                <div key={key} className="sim-truth" data-token={token}>
                  <div className="sim-truth-head">
                    <span style={{ textTransform: "capitalize" }}>{key}</span>
                    <span className="num">
                      {(block.recall * 100).toFixed(0)}% <em className="sim-truth-base">P {(block.precision * 100).toFixed(0)}%</em>
                    </span>
                  </div>
                  <div className="sim-truth-track">
                    <span className="sim-truth-fill" style={{ width: `${block.recall * 100}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="card card-pad">
          <h3 className="card-title">Recall by fault type</h3>
          <p className="card-caption">Detector against the physics range check.</p>
          <div className="sim-truth-list">
            {result.fault_types.map((name) => {
              const value = result.per_fault_type_recall[name] ?? 0;
              const base = result.baseline_per_fault_type_recall[name] ?? 0;
              return (
                <div key={name} className="sim-truth" data-token="fault">
                  <div className="sim-truth-head">
                    <span style={{ textTransform: "capitalize" }}>{name}</span>
                    <span className="num">
                      {(value * 100).toFixed(0)}% <em className="sim-truth-base">base {(base * 100).toFixed(0)}%</em>
                    </span>
                  </div>
                  <div className="sim-truth-track">
                    <span className="sim-truth-fill" style={{ width: `${value * 100}%` }} />
                    <span className="sim-truth-tick" style={{ left: `${base * 100}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="card card-pad">
          <h3 className="card-title">What the rules said</h3>
          <p className="card-caption">Reason codes behind every flagged reading.</p>
          <div className="sim-reasons">
            {Object.entries(result.event_metrics.reason_code_counts ?? {})
              .sort((a, b) => b[1] - a[1])
              .slice(0, 5)
              .map(([code, count]) => (
                <div key={code} className="sim-reason">
                  <span className="sim-reason-name">{REASON_LABEL[code] ?? code}</span>
                  <span className="sim-reason-count num">{count}</span>
                </div>
              ))}
          </div>
          <div className="sim-vote-thresholds">
            {Object.entries(result.diagnostics.vote_thresholds).map(([name, threshold]) => (
              <span key={name} className="sim-threshold">
                <b>{name.replace("_vote", "")}</b>
                <span className="num">{threshold.toFixed(2)}</span>
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
