import type { NextConfig } from "next";

const BACKEND_URL = (
  process.env.BACKEND_URL || "http://localhost:8000"
).replace(/\/api\/?$/, ""); // normalise — strip trailing /api if present

const nextConfig: NextConfig = {
  reactCompiler: true,

  /**
   * Proxy all /api/* requests to the backend service.
   * This works for both local dev (localhost:8000) and production (Render public URL).
   * The browser never needs to know the backend hostname.
   */
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
