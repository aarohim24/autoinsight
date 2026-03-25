import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000/api";

export async function POST(req: NextRequest) {
  const sid = req.headers.get("X-Session-Id") || "";
  const body = await req.json();
  const res = await fetch(`${BACKEND}/query`, {
    method: "POST",
    headers: { "X-Session-Id": sid, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
