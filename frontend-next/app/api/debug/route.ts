import { NextResponse } from "next/server";
import { BACKEND } from "@/lib/proxy";

// GET /api/debug → shows BACKEND_URL and hits /health on the backend
export async function GET() {
  let health: unknown = null;
  let error: string | null = null;
  try {
    const res = await fetch(`${BACKEND.replace(/\/api$/, "")}/health`, {
      signal: AbortSignal.timeout(5000),
    });
    const ct = res.headers.get("content-type") || "";
    health = ct.includes("application/json") ? await res.json() : await res.text();
  } catch (err: any) {
    error = err.message;
  }
  return NextResponse.json({ backend_url: BACKEND, health, error });
}
