/**
 * Shared proxy helper for Next.js API routes.
 *
 * REQUIRED: Set BACKEND_URL in your deployment environment.
 *   Vercel dashboard → Settings → Environment Variables:
 *     BACKEND_URL = https://<your-render-backend>.onrender.com/api
 *
 *   Local dev (.env.local):
 *     BACKEND_URL = http://localhost:8000/api
 */

if (
  !process.env.BACKEND_URL ||
  process.env.BACKEND_URL.startsWith("http://backend")
) {
  console.error(
    "[proxy] WARNING: BACKEND_URL is not set or is a Docker-internal hostname. " +
    "Set BACKEND_URL to your Render backend URL in Vercel environment variables."
  );
}

export const BACKEND = (process.env.BACKEND_URL || "http://localhost:8000/api")
  .replace(/\/$/, "");

const RETRY_DELAY_MS = 6000;
const MAX_RETRIES    = 7; // 7 × 6s = 42s — within Vercel's 60s maxDuration

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function proxyFetch(
  url: string,
  init?: RequestInit
): Promise<{ data: unknown; status: number }> {
  let lastError = "Server unavailable";

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    let res: Response;

    try {
      res = await fetch(url, { ...init, cache: "no-store" });
    } catch (err: unknown) {
      throw new Error(
        `Cannot reach backend — please wait 30 seconds and try again. (${(err as Error).message})`
      );
    }

    // 502/503 = Render gateway responding while backend container is booting. Retry.
    if (res.status === 502 || res.status === 503) {
      lastError = `Server is starting up (${res.status})`;
      if (attempt < MAX_RETRIES) {
        await sleep(RETRY_DELAY_MS);
        continue;
      }
      throw new Error("Server took too long to start. Please wait 30 seconds and try again.");
    }

    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      const text = await res.text();
      // Likely pointed at wrong URL (e.g. a frontend) — log to help debug
      console.error(`[proxy] Non-JSON from ${url} (status ${res.status}):`, text.slice(0, 300));
      throw new Error(
        `Unexpected response from backend (status ${res.status}). Check BACKEND_URL environment variable.`
      );
    }

    const data = await res.json();
    return { data, status: res.status };
  }

  throw new Error(lastError);
}
