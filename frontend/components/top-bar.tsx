"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CaretRight } from "@phosphor-icons/react";

const names: Record<string, string> = {
  stations: "Stations",
  events: "Events",
  method: "Method",
  model: "Model card",
};

export function TopBar() {
  const pathname = usePathname();
  const parts = pathname.split("/").filter(Boolean);

  return (
    <div className="topbar">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link href="/">Station Integrity</Link>
        {parts.map((part, index) => {
          const href = `/${parts.slice(0, index + 1).join("/")}`;
          const isLast = index === parts.length - 1;
          const label = names[part] ?? part.toUpperCase();
          return (
            <span key={href} style={{ display: "inline-flex", alignItems: "center", gap: "0.45rem" }}>
              <CaretRight size={11} weight="bold" className="crumb-sep" aria-hidden="true" />
              {isLast ? (
                <span className="crumb-current" aria-current="page">
                  {label}
                </span>
              ) : (
                <Link href={href}>{label}</Link>
              )}
            </span>
          );
        })}
      </nav>
      <div className="topbar-actions">
        <span className="live-row">
          <span className="pulse-dot" aria-hidden="true" />
          2023 hourly · verified
        </span>
      </div>
    </div>
  );
}
