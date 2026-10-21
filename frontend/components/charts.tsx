"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TimelinePoint } from "@/lib/types";

const axisStyle = {
  fontSize: 11,
  fontFamily: "var(--font-mono), monospace",
  fill: "oklch(62% 0.01 250)",
};

const tooltipStyle = {
  background: "oklch(17.5% 0.008 255)",
  border: "1px solid oklch(31% 0.012 255)",
  borderRadius: 4,
  fontSize: 12,
  fontFamily: "var(--font-mono), monospace",
  color: "oklch(94% 0.006 90)",
};

function shortDate(value: string) {
  const date = new Date(value);
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export function NetworkTimeline({ points }: { points: TimelinePoint[] }) {
  const data = points.map((point) => ({
    ...point,
    label: shortDate(point.timestamp),
  }));

  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="anomalyFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(76% 0.145 68)" stopOpacity={0.32} />
              <stop offset="100%" stopColor="oklch(76% 0.145 68)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="oklch(26% 0.01 255)" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tick={axisStyle} tickLine={false} axisLine={false} minTickGap={40} />
          <YAxis tick={axisStyle} tickLine={false} axisLine={false} width={44} />
          <Tooltip
            contentStyle={tooltipStyle}
            labelStyle={{ color: "oklch(78% 0.008 250)" }}
            formatter={(value: number, name: string) => [value, name]}
          />
          <Area
            type="monotone"
            dataKey="anomalies"
            name="flagged readings"
            stroke="oklch(76% 0.145 68)"
            strokeWidth={1.5}
            fill="url(#anomalyFill)"
            dot={false}
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
}: {
  timestamps: string[];
  values: (number | null)[];
  anomalies: number[];
  baselineFlags: number[];
}) {
  const data = timestamps.map((timestamp, index) => ({
    label: shortDate(timestamp),
    value: values[index],
    anomaly: anomalies[index] === 1 ? values[index] : null,
    baseline: baselineFlags[index] === 1 ? values[index] : null,
  }));

  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="oklch(26% 0.01 255)" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tick={axisStyle} tickLine={false} axisLine={false} minTickGap={50} />
          <YAxis tick={axisStyle} tickLine={false} axisLine={false} width={48} domain={["auto", "auto"]} />
          <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "oklch(78% 0.008 250)" }} />
          <Line
            type="monotone"
            dataKey="value"
            name="reading"
            stroke="oklch(72% 0.05 250)"
            strokeWidth={1}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="anomaly"
            name="flagged"
            stroke="oklch(68% 0.19 22)"
            strokeWidth={0}
            dot={{ r: 2.5, fill: "oklch(68% 0.19 22)", strokeWidth: 0 }}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="baseline"
            name="range-check"
            stroke="oklch(84% 0.14 92)"
            strokeWidth={0}
            dot={{ r: 2, fill: "oklch(84% 0.14 92)", strokeWidth: 0 }}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
