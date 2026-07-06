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

/**
 * Fetch with automatic retry on network errors (e.g. Render cold start).
 * Retries up to `maxRetries` times with an exponential backoff.
 */
async function fetchWithRetry(
  url: string,
  init: RequestInit,
  maxRetries = 3,
  baseDelayMs = 3000
): Promise<Response> {
  let lastErr: unknown;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(url, { ...init, cache: "no-store" });
      return res;
    } catch (err: unknown) {
      lastErr = err;
      if (attempt < maxRetries) {
        // Exponential backoff: 3s, 6s, 12s
        await new Promise((r) => setTimeout(r, baseDelayMs * 2 ** attempt));
      }
    }
  }
  throw lastErr;
}

export async function proxyFetch(
  url: string,
  init?: RequestInit
): Promise<{ data: unknown; status: number }> {
  let res: Response;
  try {
    res = await fetchWithRetry(url, init ?? {});
  } catch (err: unknown) {
    throw new Error(
      `Backend unreachable — the server may be starting up, please try again in 30 seconds. (${(err as Error).message})`
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
