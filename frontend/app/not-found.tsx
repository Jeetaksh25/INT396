import Link from "next/link";
import { TopBar } from "@/components/top-bar";

export default function NotFound() {
  return (
    <>
      <TopBar />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: "1rem",
          paddingTop: "4rem",
          maxWidth: "48ch",
        }}
      >
        <span className="chip" data-tone="neutral">
          404
        </span>
        <h1 className="page-title" style={{ fontSize: "clamp(2rem, 4vw, 3rem)" }}>
          That page is not part of the network
        </h1>
        <p className="page-sub" style={{ marginTop: 0 }}>
          The route you asked for does not exist. Station pages are keyed by their three-letter id.
        </p>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <Link href="/" className="btn btn-primary">
            Network overview
          </Link>
          <Link href="/stations" className="btn">
            All stations
          </Link>
        </div>
      </div>
    </>
  );
}
