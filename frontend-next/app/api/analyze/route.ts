import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000/api";

export async function GET(req: NextRequest) {
  const sid = req.headers.get("X-Session-Id") || "";
  const res = await fetch(`${BACKEND}/analyze`, {
    headers: { "X-Session-Id": sid },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
