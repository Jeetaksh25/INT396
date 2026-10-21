"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TimelinePoint } from "@/lib/types";

const ink = "var(--ink-3)";

const axisTick = {
  fontSize: 11,
  fill: "oklch(54% 0.011 265)",
  letterSpacing: 0,
};

const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--hairline-strong)",
  borderRadius: 10,
  fontSize: 12,
  color: "var(--ink)",
  boxShadow: "0 12px 32px -14px oklch(20% 0.01 265 / 0.22)",
  padding: "8px 10px",
  letterSpacing: "-0.01em",
};

const shortDate = (value: string) =>
  new Date(value).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });

export function NetworkTimeline({ points }: { points: TimelinePoint[] }) {
  const data = points.map((point) => ({
    label: shortDate(point.timestamp),
    anomalies: point.anomalies,
    faults: point.fault_flags,
    extremes: point.extreme_flags,
  }));

  return (
    <div className="chart-frame-lg">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="anomalyFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(58% 0.19 268)" stopOpacity={0.16} />
              <stop offset="100%" stopColor="oklch(58% 0.19 268)" stopOpacity={0.01} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            minTickGap={46}
            dy={6}
          />
          <YAxis
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={44}
            domain={[0, "dataMax + 1"]}
            allowDecimals={false}
          />
          <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: "var(--hairline-strong)" }} />
          <Area
            type="monotone"
            dataKey="anomalies"
            name="All flags"
            stroke="oklch(58% 0.19 268)"
            strokeWidth={1.6}
            fill="url(#anomalyFill)"
            dot={false}
            activeDot={{ r: 3.5, strokeWidth: 0 }}
          />
          <Line
            type="monotone"
            dataKey="faults"
            name="Fault verdict"
            stroke="oklch(58% 0.20 25)"
            strokeWidth={1.3}
            dot={false}
            strokeDasharray="4 3"
          />
          <Line
            type="monotone"
            dataKey="extremes"
            name="Extreme verdict"
            stroke="oklch(56% 0.15 248)"
            strokeWidth={1.3}
            dot={false}
            strokeDasharray="4 3"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SensorLineChart({
  timestamps,
  values,
  anomalies,
  baselineFlags,
  unit,
}: {
  timestamps: string[];
  values: (number | null)[];
  anomalies: number[];
  baselineFlags: number[];
  unit?: string;
}) {
  const data = timestamps.map((timestamp, index) => ({
    label: shortDate(timestamp),
    value: values[index],
    anomaly: anomalies[index] === 1 ? values[index] : null,
    baseline: baselineFlags[index] === 1 ? values[index] : null,
  }));

  return (
    <div className="chart-frame-lg">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: -14 }}>
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            minTickGap={54}
            dy={6}
          />
          <YAxis
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={48}
            domain={["auto", "auto"]}
          />
          <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: "var(--hairline-strong)" }} />
          <Line
            type="monotone"
            dataKey="value"
            name="Reading"
            stroke="oklch(48% 0.02 265)"
            strokeWidth={1.1}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="anomaly"
            name="Consensus flag"
            stroke="transparent"
            strokeWidth={0}
            dot={{ r: 2.4, fill: "oklch(58% 0.20 25)", strokeWidth: 0 }}
            connectNulls={false}
            activeDot={false}
          />
          <Line
            type="monotone"
            dataKey="baseline"
            name="Range check"
            stroke="transparent"
            strokeWidth={0}
            dot={{ r: 1.8, fill: "oklch(64% 0.14 78)", strokeWidth: 0 }}
            connectNulls={false}
            activeDot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function VoteDistribution({
  agreementShare,
  threshold,
}: {
  agreementShare: Record<string, number>;
  threshold: number;
}) {
  const data = Object.entries(agreementShare).map(([votes, share]) => ({
    votes,
    percent: Number((share * 100).toFixed(3)),
    flagged: Number(votes) >= threshold,
  }));
  const peak = Math.max(...data.map((entry) => entry.percent), 1);
  const axisMax = Math.max(5, Math.ceil(peak / 5) * 5);
  const axisTicks = [0, axisMax / 4, axisMax / 2, (axisMax * 3) / 4, axisMax].map((value) =>
    Number(value.toFixed(2)),
  );

  return (
    <div className="chart-frame-sm">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -22 }}>
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="votes"
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            dy={6}
            label={{
              value: "votes of 5",
              position: "insideBottomRight",
              offset: -2,
              style: { fontSize: 10, fill: ink },
            }}
          />
          <YAxis
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={46}
            domain={[0, axisMax]}
            ticks={axisTicks}
            tickFormatter={(value: number) => `${value}%`}
          />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--surface-sunken)" }} />
          <ReferenceLine x={String(threshold)} stroke="var(--accent)" strokeDasharray="4 3" />
          <Bar dataKey="percent" name="share of readings" radius={[6, 6, 0, 0]} maxBarSize={54}>
            {data.map((entry) => (
              <Cell
                key={entry.votes}
                fill={entry.flagged ? "oklch(58% 0.19 268)" : "oklch(86% 0.007 265)"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
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
  const faultTypes = Object.keys(detector);
  const data = faultTypes.map((name) => ({
    name,
    detector: Number((detector[name] * 100).toFixed(1)),
    baseline: Number(((baseline[name] ?? 0) * 100).toFixed(1)),
  }));

  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }} barGap={3}>
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="name"
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            dy={6}
            interval={0}
          />
          <YAxis
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={44}
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tickFormatter={(value: number) => `${value}%`}
          />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--surface-sunken)" }} />
          <Bar
            dataKey="detector"
            name="Consensus"
            fill="oklch(58% 0.19 268)"
            radius={[5, 5, 0, 0]}
            maxBarSize={26}
          />
          <Bar
            dataKey="baseline"
            name="Range check"
            fill="oklch(86% 0.007 265)"
            radius={[5, 5, 0, 0]}
            maxBarSize={26}
          />
        </BarChart>
      </ResponsiveContainer>
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
  const data = [
    {
      name: "Fault",
      rate: Number(((confusion.fault_flagged / Math.max(confusion.fault_total, 1)) * 100).toFixed(2)),
      fill: "oklch(58% 0.20 25)",
    },
    {
      name: "Extreme",
      rate: Number(
        ((confusion.extreme_flagged / Math.max(confusion.extreme_total, 1)) * 100).toFixed(2),
      ),
      fill: "oklch(56% 0.15 248)",
    },
    {
      name: "Clean",
      rate: Number(
        ((confusion.clean_flagged / Math.max(confusion.clean_total, 1)) * 100).toFixed(2),
      ),
      fill: "oklch(70% 0.008 265)",
    },
  ];

  return (
    <div className="chart-frame-sm">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -22 }}>
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={axisTick} tickLine={false} axisLine={false} dy={6} />
          <YAxis
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={46}
            domain={[0, Math.max(5, Math.ceil(Math.max(...data.map((entry) => entry.rate)) / 5) * 5)]}
            tickFormatter={(value: number) => `${value}%`}
          />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--surface-sunken)" }} />
          <Bar dataKey="rate" radius={[6, 6, 0, 0]} maxBarSize={64}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
