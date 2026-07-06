/**
 * API client for AutoInsight.
 *
 * The browser calls the backend directly using NEXT_PUBLIC_API_URL.
 * No server-side proxy or rewrites needed.
 *
 * Set NEXT_PUBLIC_API_URL in your environment:
 *   - Local dev:  http://localhost:8000/api
 *   - Production: https://autoinsight-lc8i.onrender.com/api
 */

import type {
  UploadMeta,
  AnalyzeResponse,
  InsightResult,
  QueryResult,
  SessionStatus,
} from "./types";

// Trim trailing slash so `/api//upload-data` never happens
const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
).replace(/\/$/, "");

function buildHeaders(sessionId?: string): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (sessionId) {
    headers["X-Session-Id"] = sessionId;
  }
  return headers;
}

async function parseResponse<T>(res: Response, fallbackMessage: string): Promise<T> {
  if (!res.ok) {
    let detail = fallbackMessage;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // ignore JSON parse failure — keep fallbackMessage
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function uploadCSV(file: File): Promise<UploadMeta> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/upload-data`, {
    method: "POST",
    body: form,
    // Do NOT set Content-Type — browser must set it with the multipart boundary
  });
  return parseResponse<UploadMeta>(res, "Upload failed");
}

export async function analyze(sessionId: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    headers: buildHeaders(sessionId),
  });
  return parseResponse<AnalyzeResponse>(res, "Analysis failed");
}

export async function generateInsights(sessionId: string): Promise<InsightResult> {
  const res = await fetch(`${API_BASE}/generate-insights`, {
    method: "POST",
    headers: buildHeaders(sessionId),
  });
  return parseResponse<InsightResult>(res, "Failed to generate insights");
}

export async function askQuestion(sessionId: string, question: string): Promise<QueryResult> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: buildHeaders(sessionId),
    body: JSON.stringify({ question }),
  });
  return parseResponse<QueryResult>(res, "Query failed");
}

export async function getSessionStatus(sessionId: string): Promise<SessionStatus> {
  const res = await fetch(`${API_BASE}/session/status`, {
    headers: buildHeaders(sessionId),
  });
  return parseResponse<SessionStatus>(res, "Session status check failed");
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/session`, {
    method: "DELETE",
    headers: buildHeaders(sessionId),
  });
}
