import { NextResponse } from "next/server";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const seed = new URL(request.url).searchParams.get("seed");
  const suffix = seed ? `?seed=${encodeURIComponent(seed)}` : "";

  try {
    const response = await fetch(`${BASE_URL}/api/simulation/run${suffix}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(600_000),
    });
    if (!response.ok) {
      return NextResponse.json(
        { error: "simulation upstream failed" },
        { status: response.status },
      );
    }
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "backend unreachable" }, { status: 502 });
  }
}
