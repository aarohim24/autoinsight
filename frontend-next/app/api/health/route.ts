import { NextResponse } from "next/server";
import { BACKEND } from "@/lib/proxy";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/health`, {
      cache: "no-store",
      // Short timeout — this is just a wake-up ping, not critical
      signal: AbortSignal.timeout(8000),
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json({ ok: res.ok, ...data }, { status: res.ok ? 200 : 503 });
  } catch {
    // Backend still starting up — return 503 so the UI knows
    return NextResponse.json({ ok: false, detail: "Backend starting up" }, { status: 503 });
  }
}
