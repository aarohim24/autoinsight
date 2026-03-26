/**
 * Shared proxy helper for Next.js API routes.
 * Handles non-JSON responses from the backend gracefully.
 */
export const BACKEND = (
  process.env.BACKEND_URL || "http://localhost:8000/api"
).replace(/\/$/, ""); // strip trailing slash

export async function proxyFetch(
  url: string,
  init?: RequestInit
): Promise<{ data: unknown; status: number }> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err: any) {
    throw new Error(`Backend unreachable (${BACKEND}): ${err.message}`);
  }

  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    const text = await res.text();
    throw new Error(
      `Backend returned non-JSON (status ${res.status}): ${text.slice(0, 200)}`
    );
  }

  const data = await res.json();
  return { data, status: res.status };
}
