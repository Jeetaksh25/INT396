import Link from "next/link";
import { NetworkOverview } from "@/components/overview";

export const dynamic = "force-dynamic";

export default function HomePage() {
  return (
    <>
      <header className="page-head">
        <div>
          <h1 className="page-title">Which instruments are lying to you?</h1>
          <p className="page-sub">
            Eight Indian weather stations, one year of hourly ERA5 readings, five unsupervised
            detectors in consensus, and a rule tree that separates a broken sensor from a real
            heat wave.
          </p>
        </div>
        <div className="stamp">
          <div>INT-396 · Unsupervised Learning</div>
          <div>SEED 42 · 2023 hourly · CCS BY 4.0</div>
        </div>
      </header>

      <NetworkOverview />

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">Where the evidence lives</h2>
          <span className="section-note">three views, one pipeline</span>
        </div>
        <div className="note-list">
          <p>
            <Link href="/stations" className="row-link">
              Stations
            </Link>{" "}
            ranks each site by trailing-window health, fault counts and anomalous share, then opens
            the full hour-by-hour trace for any sensor.
          </p>
          <p>
            <Link href="/events" className="row-link">
              Detection events
            </Link>{" "}
            lists the grouped anomaly episodes the discriminator classified, with the reason code
            that decided FAULT versus EXTREME.
          </p>
          <p>
            <Link href="/method" className="row-link">
              Method &amp; metrics
            </Link>{" "}
            shows the baseline comparison, the per-fault-type recall breakdown and the exact
            definitions behind every number on this page.
          </p>
        </div>
      </section>
    </>
  );
}
