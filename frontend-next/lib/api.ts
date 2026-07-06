/**
 * API client for AutoInsight.
 * All fetch calls hit /api/* which Next.js rewrites to the backend via next.config.ts.
 * No server-side proxy files needed — the rewrite is handled transparently.
 */

import type {
  UploadMeta,
  AnalyzeResponse,
  InsightResult,
  QueryResult,
  SessionStatus,
} from "./types";

const API_BASE = "/api";

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
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? fallbackMessage);
  }
  return res.json() as Promise<T>;
}

export async function uploadCSV(file: File): Promise<UploadMeta> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/upload-data`, {
    method: "POST",
    body: form,
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
