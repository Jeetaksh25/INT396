export function ChartSkeleton({ height = 260 }: { height?: number }) {
  return (
    <div
      style={{ height }}
      aria-hidden="true"
      role="presentation"
      className="panel-skeleton"
    />
  );
}

export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div aria-busy="true" aria-live="polite" className="panel-skeleton-stack">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="panel-skeleton-line" aria-hidden="true" />
      ))}
    </div>
  );
}

export function SectionSkeleton() {
  return (
    <div className="section" aria-busy="true">
      <div className="panel-skeleton-line" aria-hidden="true" />
      <TableSkeleton rows={5} />
    </div>
  );
}
