export const maxDuration = 60; // Allow up to 60s for Render cold start
import { NextRequest, NextResponse } from "next/server";
import { BACKEND, proxyFetch } from "@/lib/proxy";

export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const { data, status } = await proxyFetch(`${BACKEND}/upload-data`, {
      method: "POST",
      body: form,
    });
    return NextResponse.json(data, { status });
  } catch (err: unknown) {
    return NextResponse.json(
      { detail: (err as Error).message },
      { status: 502 }
    );
  }
}
