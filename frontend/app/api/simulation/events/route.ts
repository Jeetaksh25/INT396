import { NextResponse } from "next/server";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function GET(request: Request) {
  const seed = new URL(request.url).searchParams.get("seed") ?? "1";

  try {
    const response = await fetch(
      `${BASE_URL}/api/simulation/events?seed=${encodeURIComponent(seed)}`,
      {
        cache: "no-store",
        headers: { Accept: "text/event-stream" },
        signal: AbortSignal.timeout(600_000),
      },
    );
    if (!response.ok || !response.body) {
      return NextResponse.json(
        { error: "simulation upstream failed" },
        { status: response.status || 502 },
      );
    }

    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    return NextResponse.json({ error: "backend unreachable" }, { status: 502 });
  }
}
