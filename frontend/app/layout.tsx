import type { Metadata } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import "./globals.css";
import { RailNav } from "@/components/rail-nav";

const bodyFont = Geist({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const displayFont = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
  display: "swap",
});

const monoFont = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Network Health · Sensor Fault Discovery",
  description:
    "Unsupervised detection of failing weather-station sensors and separation from genuine extreme events.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${bodyFont.variable} ${displayFont.variable} ${monoFont.variable}`}>
        <div className="shell">
          <RailNav />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
