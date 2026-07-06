import { NextRequest, NextResponse } from "next/server";
import { BACKEND, proxyFetch } from "@/lib/proxy";

export async function GET(req: NextRequest) {
  try {
    const sid = req.headers.get("X-Session-Id") || "";
    const { data, status } = await proxyFetch(`${BACKEND}/session/status`, {
      headers: { "X-Session-Id": sid },
    });
    return NextResponse.json(data, { status });
  } catch (err: unknown) {
    return NextResponse.json(
      { detail: (err as Error).message },
      { status: 502 }
    );
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const sid = req.headers.get("X-Session-Id") || "";
    const { data, status } = await proxyFetch(`${BACKEND}/session`, {
      method: "DELETE",
      headers: { "X-Session-Id": sid },
    });
    return NextResponse.json(data, { status });
  } catch (err: unknown) {
    return NextResponse.json(
      { detail: (err as Error).message },
      { status: 502 }
    );
  }
}
