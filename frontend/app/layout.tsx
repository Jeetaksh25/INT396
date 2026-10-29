import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { RailNav } from "@/components/rail-nav";
import { MotionProvider } from "@/components/motion";
import { ScrollReset } from "@/components/scroll-reset";
import { TooltipProvider } from "@/components/ui/tooltip";

const bodyFont = Geist({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
  fallback: ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
});

const displayFont = Geist({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["400", "500", "600"],
  fallback: ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
});

const monoFont = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Station Integrity · Sensor Fault Discovery",
    template: "%s · Station Integrity",
  },
  description:
    "Supervised classification of failing weather-station sensors versus genuine extreme events. Eight ERA5 stations, one Random Forest.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${bodyFont.variable} ${displayFont.variable} ${monoFont.variable}`}>
        <MotionProvider>
          <TooltipProvider delayDuration={220}>
            <ScrollReset />
            <div className="grain" aria-hidden="true" />
            <div className="shell">
              <RailNav />
              <main className="main">
                <div className="content">{children}</div>
              </main>
            </div>
          </TooltipProvider>
        </MotionProvider>
      </body>
    </html>
  );
}
