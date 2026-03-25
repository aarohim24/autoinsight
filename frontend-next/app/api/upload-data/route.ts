import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000/api";

export async function POST(req: NextRequest) {
  const form = await req.formData();
  const res = await fetch(`${BACKEND}/upload-data`, {
    method: "POST",
    body: form,
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
