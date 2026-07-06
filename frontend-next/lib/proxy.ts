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

const RETRY_DELAY_MS = 6000; // 6s between retries
const MAX_RETRIES    = 7;    // 7 × 6s = 42s max wait — within Vercel's 60s maxDuration

/**
 * Sleep helper.
 */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Proxy a request to the backend, retrying on 502 (Render cold-start gateway errors).
 * Render returns an HTML 502 page instantly while the app container is booting.
 * We keep retrying until the container is ready or we run out of time.
 */
export async function proxyFetch(
  url: string,
  init?: RequestInit
): Promise<{ data: unknown; status: number }> {
  let lastError = "Unknown error";

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    let res: Response;

    try {
      res = await fetch(url, { ...init, cache: "no-store" });
    } catch (err: unknown) {
      // True network failure (DNS, connection refused etc.) — no point retrying
      throw new Error(
        `The server is starting up — please wait a moment and try again. (${(err as Error).message})`
      );
    }

    // 502 from Render's gateway = backend container still booting. Retry.
    if (res.status === 502 || res.status === 503) {
      lastError = `Service unavailable (${res.status}) — server is starting up`;
      if (attempt < MAX_RETRIES) {
        await sleep(RETRY_DELAY_MS);
        continue;
      }
      throw new Error(
        `The server took too long to start. Please wait 30 seconds and try again.`
      );
    }

    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      const text = await res.text();
      throw new Error(
        `Unexpected response (status ${res.status}): ${text.slice(0, 200)}`
      );
    }

    const data = await res.json();
    return { data, status: res.status };
  }

  throw new Error(lastError);
}
