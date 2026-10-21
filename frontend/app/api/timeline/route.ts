import { NextResponse } from "next/server";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function GET(request: Request) {
  const days = new URL(request.url).searchParams.get("days") ?? "30";

  try {
    const response = await fetch(`${BASE_URL}/api/timeline?days=${days}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return NextResponse.json({ error: "upstream failed" }, { status: response.status });
    }
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "upstream unreachable" }, { status: 502 });
  }
}
