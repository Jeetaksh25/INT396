import { Badge } from "@/components/ui/badge";
import { StationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const statusLabel: Record<StationStatus, string> = {
  HEALTHY: "Healthy",
  WATCH: "Watch",
  FAULT: "Fault",
  EXTREME_EVENT: "Extreme",
};

const statusTone: Record<StationStatus, string> = {
  HEALTHY: "bg-[var(--healthy-soft)] text-[oklch(42%_0.13_158)] border-[oklch(90%_0.05_158)]",
  WATCH: "bg-[var(--watch-soft)] text-[oklch(46%_0.12_70)] border-[oklch(90%_0.07_78)]",
  FAULT: "bg-[var(--fault-soft)] text-[oklch(48%_0.18_25)] border-[oklch(90%_0.05_25)]",
  EXTREME_EVENT: "bg-[var(--extreme-soft)] text-[oklch(46%_0.14_248)] border-[oklch(90%_0.05_248)]",
};

export function StatusBadge({ status }: { status: StationStatus }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        statusTone[status],
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {statusLabel[status]}
    </Badge>
  );
}

const verdictTone: Record<string, string> = {
  FAULT: "bg-[var(--fault-soft)] text-[oklch(48%_0.18_25)] border-[oklch(90%_0.05_25)]",
  EXTREME: "bg-[var(--extreme-soft)] text-[oklch(46%_0.14_248)] border-[oklch(90%_0.05_248)]",
};

export function VerdictBadge({ label }: { label: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        verdictTone[label] ?? "bg-[var(--surface-sunken)] text-[var(--ink-3)]",
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {label.toLowerCase()}
    </Badge>
  );
}

const sensorLabel: Record<string, string> = {
  temperature: "Temperature",
  humidity: "Humidity",
  wind_speed: "Wind speed",
  pressure: "Pressure",
};

export function SensorTag({ sensorName }: { sensorName: string }) {
  return (
    <span className="text-sm text-[var(--ink-2)]">
      {sensorLabel[sensorName] ?? sensorName}
    </span>
  );
}

export function DeltaChip({
  value,
  suffix = "pp",
  invert = false,
}: {
  value: number;
  suffix?: string;
  invert?: boolean;
}) {
  const positive = value > 0;
  const good = invert ? !positive : positive;
  if (Math.abs(value) < 1e-9) {
    return (
      <span className="chip" data-tone="neutral">
        0{suffix}
      </span>
    );
  }
  return (
    <span className="chip" data-tone={good ? "up" : "down"}>
      {positive ? "+" : "−"}
      {Math.abs(value * 100).toFixed(1)}
      {suffix}
    </span>
  );
}
