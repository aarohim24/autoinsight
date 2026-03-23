const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
function h(sid?: string): HeadersInit {
  const headers: Record<string,string> = {"Content-Type":"application/json"};
  if (sid) headers["X-Session-Id"] = sid;
  return headers;
}
export async function uploadCSV(file: File) {
  const form = new FormData(); form.append("file", file);
  const res = await fetch(`${API_BASE}/upload-data`, {method:"POST",body:form});
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail||"Upload failed"); }
  return res.json();
}
export async function analyze(sid: string) {
  const res = await fetch(`${API_BASE}/analyze`, {headers:h(sid)});
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail||"Analysis failed"); }
  return res.json();
}
export async function generateInsights(sid: string) {
  const res = await fetch(`${API_BASE}/generate-insights`, {method:"POST",headers:h(sid)});
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail||"Failed"); }
  return res.json();
}
export async function askQuestion(sid: string, question: string) {
  const res = await fetch(`${API_BASE}/query`, {method:"POST",headers:h(sid),body:JSON.stringify({question})});
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail||"Failed"); }
  return res.json();
}
