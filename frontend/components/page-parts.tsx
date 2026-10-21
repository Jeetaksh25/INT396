import { ReactNode } from "react";
import { NumberTicker } from "@/components/ui/number-ticker";

export function TickedNumber({
  value,
  decimals = 0,
  suffix = "",
}: {
  value: number;
  decimals?: number;
  suffix?: string;
}) {
  return (
    <span style={{ whiteSpace: "nowrap" }}>
      <NumberTicker value={value} decimalPlaces={decimals} />
      {suffix}
    </span>
  );
}
import { BlurFade } from "@/components/ui/blur-fade";
import { DeltaChip } from "@/components/badges";
import { cn } from "@/lib/utils";

export function PageHead({
  title,
  description,
  aside,
  size = "default",
}: {
  title: ReactNode;
  description?: string;
  aside?: ReactNode;
  size?: "default" | "large";
}) {
  return (
    <header className="page-head">
      <div className="page-head-copy">
        <BlurFade delay={0.04} duration={0.3} offset={14}>
          <h1 className={size === "large" ? "page-title-lg" : "page-title"}>{title}</h1>
        </BlurFade>
        {description ? (
          <BlurFade delay={0.1} duration={0.3} offset={12}>
            <p className="page-sub">{description}</p>
          </BlurFade>
        ) : null}
      </div>
      {aside ? (
        <BlurFade delay={0.14} duration={0.28} offset={10}>
          <div className="page-aside">{aside}</div>
        </BlurFade>
      ) : null}
    </header>
  );
}

export function Section({
  title,
  note,
  action,
  children,
  id,
}: {
  title: string;
  note?: string;
  action?: ReactNode;
  children: ReactNode;
  id?: string;
}) {
  return (
    <section className="section" id={id}>
      <div className="section-head">
        <div>
          <h2 className="section-title">{title}</h2>
          {note ? <p className="section-note" style={{ marginTop: "0.2rem" }}>{note}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function MetricCard({
  label,
  value,
  decimals = 0,
  suffix = "",
  format = "number",
  delta,
  deltaInvert = false,
  caption,
  delay = 0,
}: {
  label: string;
  value: number;
  decimals?: number;
  suffix?: string;
  format?: "number" | "percent";
  delta?: number;
  deltaInvert?: boolean;
  caption?: string;
  delay?: number;
}) {
  const displayValue = format === "percent" ? value * 100 : value;
  return (
    <BlurFade delay={delay} duration={0.32} offset={16}>
      <div className="metric">
        <div className="metric-top">
          <span className="metric-label">{label}</span>
        </div>
        <div className="metric-value">
          <TickedNumber value={displayValue} decimals={decimals} suffix={suffix} />
        </div>
        <div className="metric-foot">
          {typeof delta === "number" ? (
            <DeltaChip value={delta} invert={deltaInvert} />
          ) : null}
          {caption ? <span>{caption}</span> : null}
        </div>
      </div>
    </BlurFade>
  );
}

export function KvList({
  rows,
  className,
}: {
  rows: { key: string; value: ReactNode }[];
  className?: string;
}) {
  return (
    <div className={cn("def-list", className)}>
      {rows.map((row) => (
        <div key={row.key} className="def-row">
          <span className="def-key">{row.key}</span>
          <span className="def-value">{row.value}</span>
        </div>
      ))}
    </div>
  );
}

export function Callout({
  icon,
  children,
}: {
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="callout">
      {icon}
      <div>{children}</div>
    </div>
  );
}

export function StepList({ steps }: { steps: { title: string; body: ReactNode }[] }) {
  return (
    <div className="step-list">
      {steps.map((step, index) => (
        <div className="step" key={step.title}>
          <span className="step-index" aria-hidden="true">
            {index + 1}
          </span>
          <div className="step-body">
            <strong>{step.title}</strong> — {step.body}
          </div>
        </div>
      ))}
    </div>
  );
}
