"use client";

import { useEffect, useState } from "react";

interface SessionExpiredBannerProps {
  onGoHome: () => void;
}

export function SessionExpiredBanner({ onGoHome }: SessionExpiredBannerProps) {
  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0,0,0,0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
    >
      <div
        className="panel"
        style={{
          padding: "32px 40px",
          maxWidth: 400,
          textAlign: "center",
          borderColor: "rgba(239,68,68,0.3)",
        }}
      >
        <div style={{ fontSize: 32, marginBottom: 16 }}>⏱</div>
        <h2
          style={{
            fontFamily: "var(--font-sans)",
            fontWeight: 600,
            fontSize: "1.1rem",
            color: "var(--text)",
            marginBottom: 8,
            letterSpacing: "-0.02em",
          }}
        >
          Session Expired
        </h2>
        <p
          style={{
            color: "var(--text-3)",
            fontSize: "0.82rem",
            lineHeight: 1.6,
            marginBottom: 24,
            fontFamily: "var(--font-mono)",
          }}
        >
          Your session has expired after 1 hour of inactivity.
          Upload your CSV again to start a new session.
        </p>
        <button className="btn btn-primary" onClick={onGoHome}>
          Upload New File
        </button>
      </div>
    </div>
  );
}

interface SessionTtlBadgeProps {
  ttlSeconds: number | null;
  onExpired: () => void;
}

export function SessionTtlBadge({ ttlSeconds, onExpired }: SessionTtlBadgeProps) {
  // Initialise directly from prop — avoids calling setState synchronously in effect
  const [remaining, setRemaining] = useState<number | null>(ttlSeconds);

  useEffect(() => {
    if (ttlSeconds === null) return;

    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(interval);
          onExpired();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [ttlSeconds, onExpired]);

  if (remaining === null) return null;

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const isWarning = remaining < 300; // < 5 min

  return (
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 10,
        color: isWarning ? "var(--warn)" : "var(--text-3)",
        background: isWarning ? "rgba(245,158,11,0.1)" : "var(--bg-3)",
        padding: "2px 8px",
        borderRadius: 4,
        letterSpacing: "0.02em",
        transition: "color 0.3s, background 0.3s",
      }}
      title="Session expires in"
    >
      {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
    </span>
  );
}
