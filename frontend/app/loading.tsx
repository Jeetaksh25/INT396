export default function Loading() {
  return (
    <div className="content" style={{ paddingTop: "1rem" }}>
      <div className="skeleton" style={{ height: "2.5rem", width: "42%" }} />
      <div className="skeleton" style={{ height: "1rem", width: "62%", marginTop: "1rem" }} />
      <div className="metric-grid" style={{ marginTop: "2rem" }}>
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="skeleton" style={{ height: "7.5rem" }} />
        ))}
      </div>
      <div className="skeleton" style={{ height: "20rem", marginTop: "2rem" }} />
    </div>
  );
}
