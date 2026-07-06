export const maxDuration = 60; // Allow up to 60s for Render cold start
import { NextRequest, NextResponse } from "next/server";
import { BACKEND, proxyFetch } from "@/lib/proxy";

export async function POST(req: NextRequest) {
  try {
    const sid = req.headers.get("X-Session-Id") || "";
    const { data, status } = await proxyFetch(`${BACKEND}/generate-insights`, {
      method: "POST",
      headers: { "X-Session-Id": sid, "Content-Type": "application/json" },
    });
    return NextResponse.json(data, { status });
  } catch (err: unknown) {
    return NextResponse.json(
      { detail: (err as Error).message },
      { status: 502 }
    );
  }
}
