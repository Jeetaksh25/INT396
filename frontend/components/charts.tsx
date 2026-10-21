"use client";

import { useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts";
import {
  ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  useChart,
} from "@/components/ui/chart";
import { TimelinePoint } from "@/lib/types";

const ACCENT = "oklch(58% 0.19 268)";
const FAULT = "oklch(58% 0.20 25)";
const EXTREME = "oklch(56% 0.15 248)";
const WATCH = "oklch(64% 0.14 78)";
const HAIRLINE = "oklch(86% 0.007 265)";
const INK = "oklch(38% 0.012 265)";
const DIM = "oklch(66% 0.009 265)";

const axisTick = { fontSize: 11, fill: "oklch(54% 0.011 265)", letterSpacing: 0 };

const timelineConfig = {
  anomalies: { label: "All flags", color: INK },
  faults: { label: "Fault verdict", color: FAULT },
  extremes: { label: "Extreme verdict", color: EXTREME },
} satisfies ChartConfig;

const sensorConfig = {
  value: { label: "Reading", color: INK },
  anomaly: { label: "Consensus flag", color: FAULT },
  baseline: { label: "Range-check flag", color: WATCH },
} satisfies ChartConfig;

const recallConfig = {
  detector: { label: "Consensus", color: ACCENT },
  baseline: { label: "Range check", color: HAIRLINE },
} satisfies ChartConfig;

const confusionConfig = {
  flagged: { label: "Flagged", color: ACCENT },
  clear: { label: "Not flagged", color: "oklch(94% 0.005 265)" },
} satisfies ChartConfig;

const toEpoch = (value: string) => Date.parse(value.replace(" ", "T"));

const dayLabel = (ts: number) =>
  new Date(ts).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });

const hourLabel = (ts: number) =>
  new Date(ts).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

const faultNames: Record<string, string> = {
  bias: "Bias",
  drift: "Drift",
  stuck: "Stuck",
  spike: "Spike",
  precision: "Precision",
  dropout: "Dropout",
};

const ranges = [7, 30, 90];

const ANIM = 420;

function SensorTooltip({
  active,
  payload,
  unit,
}: {
  active?: boolean;
  payload?: { payload?: { ts: number; value: number | null; anomaly: number | null; baseline: number | null } }[];
  unit?: string;
}) {
  const { config } = useChart();
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  if (!row) return null;

  const reading = row.value === null || row.value === undefined ? "missing" : `${row.value.toFixed(1)}${unit ? ` ${unit}` : ""}`;

  return (
    <div className="chart-tip">
      <div className="chart-tip-title">{hourLabel(row.ts)}</div>
      <div className="chart-tip-row">
        <span className="chart-tip-label">
          <span className="swatch" style={{ background: INK }} />
          {config.value?.label ?? "Reading"}
        </span>
        <span className="chart-tip-value">{reading}</span>
      </div>
      {row.anomaly !== null && row.anomaly !== undefined ? (
        <div className="chart-tip-row">
          <span className="chart-tip-label">
            <span className="swatch" style={{ background: FAULT }} />
            {config.anomaly?.label ?? "Consensus"}
          </span>
          <span className="chart-tip-value">flagged</span>
        </div>
      ) : null}
      {row.baseline !== null && row.baseline !== undefined ? (
        <div className="chart-tip-row">
          <span className="chart-tip-label">
            <span className="swatch" style={{ background: WATCH }} />
            {config.baseline?.label ?? "Range check"}
          </span>
          <span className="chart-tip-value">flagged</span>
        </div>
      ) : null}
    </div>
  );
}

function bucket(points: TimelinePoint[], mode: "hour" | "day") {
  if (mode === "hour") {
    return points.map((point) => ({
      ts: toEpoch(point.timestamp),
      anomalies: point.anomalies,
      faults: point.fault_flags,
      extremes: point.extreme_flags,
    }));
  }

  const grouped: Record<string, { ts: number; anomalies: number; faults: number; extremes: number }> =
    {};

  for (const point of points) {
    const key = point.timestamp.slice(0, 10);
    const existing = grouped[key];
    if (existing) {
      existing.anomalies += point.anomalies;
      existing.faults += point.fault_flags;
      existing.extremes += point.extreme_flags;
    } else {
      grouped[key] = {
        ts: toEpoch(`${key}T00:00:00`),
        anomalies: point.anomalies,
        faults: point.fault_flags,
        extremes: point.extreme_flags,
      };
    }
  }

  return Object.values(grouped).sort((a, b) => a.ts - b.ts);
}

export function NetworkTimeline({
  points: initialPoints,
  days: initialDays = 30,
}: {
  points: TimelinePoint[];
  days?: number;
}) {
  const [days, setDays] = useState(initialDays);
  const [points, setPoints] = useState(initialPoints);
  const [pending, setPending] = useState(false);
  const cache = useRef<Record<number, TimelinePoint[]>>({ [initialDays]: initialPoints });

  const mode: "hour" | "day" = days <= 7 ? "hour" : "day";
  const data = useMemo(() => bucket(points, mode), [points, mode]);
  const total = useMemo(
    () => data.reduce((sum, entry) => sum + entry.anomalies, 0),
    [data],
  );
  const peak = useMemo(
    () => data.reduce((best, entry) => Math.max(best, entry.anomalies), 0),
    [data],
  );

  async function changeRange(next: number) {
    if (next === days) return;
    setDays(next);
    const cached = cache.current[next];
    if (cached) {
      setPoints(cached);
      return;
    }
    setPending(true);
    try {
      const response = await fetch(`/api/timeline?days=${next}`, { cache: "no-store" });
      if (response.ok) {
        const payload = (await response.json()) as { points: TimelinePoint[] };
        cache.current[next] = payload.points;
        setPoints(payload.points);
      }
    } catch {
      setPoints(points);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="chart-shell">
      <div className="chart-head">
        <div className="chart-summary">
          <span className="chart-summary-value">{total.toLocaleString()}</span>
          <span className="chart-summary-key">
            flagged readings · peak {peak} per {mode}
          </span>
        </div>
        <div className="pill-tabs" role="tablist" aria-label="Time range">
          {ranges.map((range) => (
            <button
              key={range}
              type="button"
              role="tab"
              aria-selected={range === days}
              className="pill-tab"
              data-active={range === days}
              onClick={() => changeRange(range)}
            >
              {range}d
            </button>
          ))}
        </div>
      </div>

      <ChartContainer
        config={timelineConfig}
        className="aspect-auto h-[320px] w-full"
        style={{ opacity: pending ? 0.45 : 1, transition: "opacity 180ms ease" }}
      >
        <AreaChart data={data} margin={{ top: 12, right: 8, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="flagFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={INK} stopOpacity={0.13} />
              <stop offset="100%" stopColor={INK} stopOpacity={0.01} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            minTickGap={44}
            tickFormatter={(value: number) => dayLabel(value)}
            dy={6}
          />
          <YAxis
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={44}
            allowDecimals={false}
            domain={[0, "auto"]}
          />
          <ChartTooltip
            cursor={{ stroke: "var(--hairline-strong)" }}
            content={
              <ChartTooltipContent
                indicator="line"
                labelFormatter={(_, payload) => {
                  const ts = payload?.[0]?.payload?.ts;
                  return typeof ts === "number"
                    ? mode === "hour"
                      ? hourLabel(ts)
                      : dayLabel(ts)
                    : "";
                }}
              />
            }
          />
          <ChartLegend content={<ChartLegendContent />} />
          <Area
            type="monotone"
            dataKey="anomalies"
            animationDuration={ANIM}
            animationEasing="ease-out"
            stroke={INK}
            strokeWidth={1.5}
            fill="url(#flagFill)"
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
          />
          <Line
            type="monotone"
            dataKey="faults"
            animationDuration={ANIM}
            stroke={FAULT}
            strokeWidth={1.3}
            dot={false}
            strokeDasharray="4 3"
          />
          <Line
            type="monotone"
            dataKey="extremes"
            animationDuration={ANIM}
            stroke={EXTREME}
            strokeWidth={1.3}
            dot={false}
            strokeDasharray="4 3"
          />
        </AreaChart>
      </ChartContainer>
    </div>
  );
}

export function SensorLineChart({
  timestamps,
  values,
  anomalies,
  baselineFlags,
  bands = [],
  unit,
}: {
  timestamps: string[];
  values: (number | null)[];
  anomalies: number[];
  baselineFlags: number[];
  bands?: { start: string; end: string; label: string }[];
  unit?: string;
}) {
  const data = timestamps.map((timestamp, index) => ({
    ts: toEpoch(timestamp),
    value: values[index],
    anomaly: anomalies[index] === 1 ? values[index] : null,
    baseline: baselineFlags[index] === 1 ? values[index] : null,
  }));

  const flagCount = anomalies.reduce((sum, entry) => sum + entry, 0);
  const suffix = unit ? ` ${unit}` : "";

  return (
    <div className="chart-shell">
      <div className="chart-head">
        <div className="chart-summary">
          <span className="chart-summary-value">{flagCount.toLocaleString()}</span>
          <span className="chart-summary-key">
            flagged hours of {timestamps.length.toLocaleString()}
          </span>
        </div>
        <div className="chart-legend-inline">
          <span className="legend-item">
            <span className="swatch" style={{ background: FAULT }} />
            consensus flag
          </span>
          <span className="legend-item">
            <span className="swatch" style={{ background: WATCH }} />
            range-check flag
          </span>
        </div>
      </div>

      <ChartContainer config={sensorConfig} className="aspect-auto h-[300px] w-full">
        <LineChart data={data} margin={{ top: 12, right: 10, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            minTickGap={54}
            tickFormatter={(value: number) => dayLabel(value)}
            dy={6}
          />
          <YAxis
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={48}
            domain={["auto", "auto"]}
            tickFormatter={(value: number) => `${value}`}
          />
          <ChartTooltip
            cursor={{ stroke: "var(--hairline-strong)" }}
            content={<SensorTooltip unit={suffix} />}
          />
          {bands.map((band) => (
            <ReferenceLine
              key={`${band.start}-${band.label}`}
              x={toEpoch(band.start)}
              stroke={band.label === "EXTREME" ? EXTREME : FAULT}
              strokeWidth={1}
              strokeOpacity={0.5}
              ifOverflow="hidden"
            />
          ))}
          <Line
            type="monotone"
            dataKey="value"
            animationDuration={ANIM}
            stroke={INK}
            strokeWidth={1.1}
            dot={false}
            activeDot={{ r: 3, strokeWidth: 0 }}
          />
          <Line
            dataKey="anomaly"
            stroke="transparent"
            strokeWidth={0}
            dot={{ r: 2.4, fill: FAULT, strokeWidth: 0 }}
            connectNulls={false}
            activeDot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="baseline"
            stroke="transparent"
            strokeWidth={0}
            dot={{ r: 1.8, fill: WATCH, strokeWidth: 0 }}
            connectNulls={false}
            activeDot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ChartContainer>
    </div>
  );
}

export function RecallBars({
  detector,
  baseline,
}: {
  detector: Record<string, number>;
  baseline: Record<string, number>;
}) {
  const data = Object.keys(detector)
    .map((name) => ({
      name: faultNames[name] ?? name,
      detector: Number((detector[name] * 100).toFixed(1)),
      baseline: Number(((baseline[name] ?? 0) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.detector - a.detector);

  const best = data.reduce((top, entry) => Math.max(top, entry.detector), 0);

  return (
    <div className="chart-shell">
      <div className="chart-head">
        <div className="chart-summary">
          <span className="chart-summary-value">{data.length}</span>
          <span className="chart-summary-key">fault types · best recall {best.toFixed(0)}%</span>
        </div>
        <div className="chart-legend-inline">
          <span className="legend-item">
            <span className="swatch" style={{ background: ACCENT }} />
            consensus
          </span>
          <span className="legend-item">
            <span className="swatch" style={{ background: HAIRLINE }} />
            range check
          </span>
        </div>
      </div>

      <ChartContainer
        config={recallConfig}
        className="aspect-auto w-full"
        style={{ height: `${Math.max(data.length * 42, 180)}px` }}
      >
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 44, bottom: 4, left: 4 }}
          barGap={2}
        >
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value: number) => `${value}%`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12, fill: INK }}
            tickLine={false}
            axisLine={false}
            width={92}
          />
          <ChartTooltip
            cursor={{ fill: "var(--surface-sunken)" }}
            content={
              <ChartTooltipContent
                indicator="line"
                formatter={(value, name) => (
                  <span className="chart-tip-row">
                    <span>{name}</span>
                    <span className="chart-tip-value">{Number(value).toFixed(1)}%</span>
                  </span>
                )}
              />
            }
          />
          <Bar
            dataKey="detector"
            fill={ACCENT}
            radius={[0, 4, 4, 0]}
            maxBarSize={11}
            animationDuration={ANIM}
            animationEasing="ease-out"
          >
            <LabelList
              dataKey="detector"
              position="right"
              offset={8}
              formatter={(value) => `${Number(value ?? 0).toFixed(0)}%`}
              style={{ fontSize: 11, fill: DIM, fontVariantNumeric: "tabular-nums" }}
            />
          </Bar>
          <Bar
            dataKey="baseline"
            fill={HAIRLINE}
            radius={[0, 4, 4, 0]}
            maxBarSize={11}
            animationDuration={ANIM}
          />
        </BarChart>
      </ChartContainer>
    </div>
  );
}

export function FlagRateBars({
  confusion,
}: {
  confusion: {
    fault_flagged: number;
    fault_total: number;
    extreme_flagged: number;
    extreme_total: number;
    clean_flagged: number;
    clean_total: number;
  };
}) {
  const rows = [
    {
      name: "Clean readings",
      rate: (confusion.clean_flagged / Math.max(confusion.clean_total, 1)) * 100,
      flagged: confusion.clean_flagged,
      total: confusion.clean_total,
      fill: HAIRLINE,
    },
    {
      name: "Extreme readings",
      rate: (confusion.extreme_flagged / Math.max(confusion.extreme_total, 1)) * 100,
      flagged: confusion.extreme_flagged,
      total: confusion.extreme_total,
      fill: EXTREME,
    },
    {
      name: "Fault readings",
      rate: (confusion.fault_flagged / Math.max(confusion.fault_total, 1)) * 100,
      flagged: confusion.fault_flagged,
      total: confusion.fault_total,
      fill: FAULT,
    },
  ];

  const maxRate = rows.reduce((top, row) => Math.max(top, row.rate), 0);
  const axisMax = Math.max(5, Math.ceil(maxRate / 5) * 5);

  return (
    <div className="chart-shell">
      <div className="chart-head">
        <div className="chart-summary">
          <span className="chart-summary-value">{rows[2].rate.toFixed(1)}%</span>
          <span className="chart-summary-key">
            of {confusion.fault_total.toLocaleString()} injected fault readings caught
          </span>
        </div>
      </div>

      <ChartContainer
        config={confusionConfig}
        className="aspect-auto w-full"
        style={{ height: "152px" }}
      >
        <BarChart data={rows} layout="vertical" margin={{ top: 2, right: 56, bottom: 2, left: 4 }}>
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, axisMax]}
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value: number) => `${value}%`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12, fill: INK }}
            tickLine={false}
            axisLine={false}
            width={118}
          />
          <ChartTooltip
            cursor={{ fill: "var(--surface-sunken)" }}
            content={
              <ChartTooltipContent
                hideIndicator
                formatter={(_, __, item) => {
                  const row = item?.payload as (typeof rows)[number] | undefined;
                  if (!row) return null;
                  return (
                    <span className="chart-tip-row">
                      <span>{row.name}</span>
                      <span className="chart-tip-value">
                        {row.flagged.toLocaleString()} / {row.total.toLocaleString()} ·{" "}
                        {row.rate.toFixed(2)}%
                      </span>
                    </span>
                  );
                }}
              />
            }
          />
          <Bar
            dataKey="rate"
            radius={[0, 5, 5, 0]}
            maxBarSize={26}
            animationDuration={ANIM}
            animationEasing="ease-out"
          >
            {rows.map((row) => (
              <Cell key={row.name} fill={row.fill} />
            ))}
            <LabelList
              dataKey="rate"
              position="right"
              offset={8}
              formatter={(value) => {
                const rate = Number(value ?? 0);
                return rate < 1 ? `${rate.toFixed(2)}%` : `${rate.toFixed(1)}%`;
              }}
              style={{ fontSize: 11, fill: DIM, fontVariantNumeric: "tabular-nums" }}
            />
          </Bar>
        </BarChart>
      </ChartContainer>
    </div>
  );
}
