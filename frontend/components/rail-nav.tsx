"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Network overview" },
  { href: "/stations", label: "Stations" },
  { href: "/events", label: "Detection events" },
  { href: "/method", label: "Method & metrics" },
];

export function RailNav() {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(href);
  }

  return (
    <aside className="rail">
      <div className="brand">
        <span className="brand-mark">INT-396</span>
        <span className="brand-name">Station Integrity</span>
      </div>

      <nav className="rail-nav" aria-label="Primary">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rail-link"
            data-active={isActive(link.href)}
          >
            <span className="rail-dot" aria-hidden="true" />
            {link.label}
          </Link>
        ))}
      </nav>

      <div className="rail-foot">
        <span>Unsupervised · k-Means · DBSCAN · PCA · Isolation Forest · LOF</span>
        <span>Open-Meteo ERA5 · 8 stations · 2023 hourly</span>
      </div>
    </aside>
  );
}
