"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  SquaresFour,
  Broadcast,
  Pulse,
  ChartLineUp,
  TreeStructure,
} from "@phosphor-icons/react";

const overviewLinks = [
  { href: "/", label: "Overview", icon: SquaresFour },
  { href: "/stations", label: "Stations", icon: Broadcast },
  { href: "/events", label: "Events", icon: Pulse },
];

const analysisLinks = [
  { href: "/method", label: "Method", icon: ChartLineUp },
  { href: "/model", label: "Model card", icon: TreeStructure },
];

export function RailNav() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="rail">
      <Link href="/" className="brand" aria-label="Station Integrity home">
        <span className="brand-mark" aria-hidden="true">
          SI
        </span>
        <span className="brand-text">
          <span className="brand-name">Station Integrity</span>
          <span className="brand-sub">INT-396 · Supervised</span>
        </span>
      </Link>

      <nav className="rail-group" aria-label="Overview">
        <span className="rail-caption">Monitor</span>
        {overviewLinks.map((link) => {
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="rail-link"
              data-active={isActive(link.href)}
              aria-current={isActive(link.href) ? "page" : undefined}
            >
              <Icon size={17} weight="regular" aria-hidden="true" />
              {link.label}
            </Link>
          );
        })}
      </nav>

      <nav className="rail-group" aria-label="Analysis">
        <span className="rail-caption">Analysis</span>
        {analysisLinks.map((link) => {
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="rail-link"
              data-active={isActive(link.href)}
              aria-current={isActive(link.href) ? "page" : undefined}
            >
              <Icon size={17} weight="regular" aria-hidden="true" />
              {link.label}
            </Link>
          );
        })}
      </nav>

      <div className="rail-foot">
        <span className="live-row">
          <span className="pulse-dot" aria-hidden="true" />
          Results cached · seed 42
        </span>
        <div className="rail-meta">
          <span>8 stations · 280,320 readings</span>
          <span>ERA5 / Open-Meteo · CC BY 4.0</span>
        </div>
      </div>
    </aside>
  );
}
