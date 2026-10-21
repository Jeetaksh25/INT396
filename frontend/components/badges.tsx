import { StationStatus } from "@/lib/types";

const labels: Record<StationStatus, string> = {
  HEALTHY: "Healthy",
  WATCH: "Watch",
  FAULT: "Fault",
  EXTREME_EVENT: "Extreme event",
};

export function StatusBadge({ status }: { status: StationStatus }) {
  return (
    <span className="badge" data-status={status}>
      {labels[status]}
    </span>
  );
}

export function LabelBadge({ label }: { label: string }) {
  return (
    <span className="badge" data-label={label}>
      {label.toLowerCase()}
    </span>
  );
}

export function SensorName({ sensorName }: { sensorName: string }) {
  return <span className="mono">{sensorName.replace("_", " ")}</span>;
}
