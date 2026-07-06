/**
 * Shared proxy helper for Next.js API routes.
 * The Next.js server proxies browser calls to the Python backend.
 *
 * Set BACKEND_URL in your deployment environment:
 *   Vercel:    https://autoinsight-lc8i.onrender.com/api
 *   Local dev: http://localhost:8000/api
 */

// Falls back to the known production Render URL so Vercel works even
// if the env var was accidentally set to the Docker-internal hostname.
export const BACKEND = (
  process.env.BACKEND_URL &&
  !process.env.BACKEND_URL.startsWith("http://backend")
    ? process.env.BACKEND_URL
    : "https://autoinsight-lc8i.onrender.com/api"
).replace(/\/$/, "");

export async function proxyFetch(
  url: string,
  init?: RequestInit
): Promise<{ data: unknown; status: number }> {
  let res: Response;
  try {
    res = await fetch(url, { ...init, cache: "no-store" });
  } catch (err: unknown) {
    throw new Error(
      `The server is starting up — please wait 30 seconds and try again. (${(err as Error).message})`
    );
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
