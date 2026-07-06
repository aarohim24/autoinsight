"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { uploadCSV, analyze } from "@/lib/api";

const FEATURES = [
  { icon: "⚡", title: "Instant Stats", desc: "Summary stats, correlations & trends in seconds" },
  { icon: "🤖", title: "AI Insights",  desc: "Groq-powered LLM finds patterns you'd miss" },
  { icon: "💬", title: "Ask Anything", desc: "Natural language Q&A about your dataset" },
  { icon: "🔒", title: "Private",      desc: "Session-isolated, auto-expires after 1 hour" },
];

const STATS = [
  { value: "CSV",  label: "Input format" },
  { value: "50MB", label: "Max file size" },
  { value: "<2s",  label: "Analysis time" },
];

function UploadIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--text-3)"
      strokeWidth="1.5"
      style={{ margin: "0 auto 12px" }}
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      className="spinner"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--accent)"
      strokeWidth="2"
    >
      <circle cx="12" cy="12" r="10" strokeOpacity="0.2" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}

// ── Upload progress steps ────────────────────────────────────────────────────
type UploadStep = "uploading" | "analysing" | "ready";

const STEP_LABELS: Record<UploadStep, string> = {
  uploading: "Uploading CSV...",
  analysing: "Running analysis...",
  ready:     "Done!",
};

export default function HomePage() {
  const router = useRouter();
  const [uploadStep, setUploadStep] = useState<UploadStep | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const isLoading = uploadStep !== null;

  const onDrop = useCallback(
    async (files: File[]) => {
      const file = files[0];
      if (!file) return;

      setUploadStep("uploading");
      setErrorMessage("");

      try {
        const meta = await uploadCSV(file);
        setUploadStep("analysing");
        const analysis = await analyze(meta.session_id);
        setUploadStep("ready");

        sessionStorage.setItem("ai_meta", JSON.stringify(meta));
        sessionStorage.setItem("ai_analysis", JSON.stringify(analysis));

        router.push("/dashboard");
      } catch (err: unknown) {
        setErrorMessage((err as Error).message);
        setUploadStep(null);
      }
    },
    [router]
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"] },
    multiple: false,
    disabled: isLoading,
    noClick: true,
  });

  return (
    <main style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* ── Nav ── */}
      <nav style={{ borderBottom: "1px solid var(--border)", padding: "0 24px" }}>
        <div
          className="container"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            height: 52,
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontWeight: 600,
              fontSize: 14,
              color: "var(--text)",
              letterSpacing: "-0.01em",
            }}
          >
            AutoInsight
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div className="dot dot-green" />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-3)" }}>
              api ready
            </span>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "60px 24px",
        }}
      >
        <div style={{ width: "100%", maxWidth: 560 }}>
          {/* Headline */}
          <div style={{ marginBottom: 36 }}>
            <p className="label" style={{ marginBottom: 14 }}>
              AI-powered data analysis
            </p>
            <h1
              style={{
                fontFamily: "var(--font-sans)",
                fontWeight: 600,
                fontSize: "2.4rem",
                lineHeight: 1.12,
                letterSpacing: "-0.04em",
                color: "var(--text)",
                marginBottom: 14,
              }}
            >
              From raw data
              <br />
              to{" "}
              <span
                style={{
                  color: "var(--accent)",
                  textShadow: "0 0 32px rgba(0,255,135,0.3)",
                }}
              >
                clear answers.
              </span>
            </h1>
            <p
              style={{
                color: "var(--text-2)",
                fontSize: "0.95rem",
                lineHeight: 1.65,
                maxWidth: 420,
              }}
            >
              Upload a CSV to get instant summary statistics, interactive charts,
              outlier detection, and AI-generated insights — all in your browser.
            </p>
          </div>

          {/* Drop zone */}
          <div
            {...getRootProps()}
            className="panel"
            style={{
              padding: "36px 32px",
              textAlign: "center",
              borderStyle: "dashed",
              borderColor: isDragActive ? "var(--accent)" : "var(--border)",
              background: isDragActive
                ? "rgba(0,255,135,0.03)"
                : "var(--bg-2)",
              transition: "var(--transition-normal)",
              cursor: "default",
              boxShadow: isDragActive
                ? "0 0 0 4px rgba(0,255,135,0.08)"
                : "none",
            }}
          >
            <input {...getInputProps()} />

            {isLoading ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 14,
                }}
              >
                <Spinner />
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                    color: "var(--text-3)",
                  }}
                >
                  {STEP_LABELS[uploadStep!]}
                </span>
                {/* Progress dots */}
                <div style={{ display: "flex", gap: 6 }}>
                  {(["uploading", "analysing", "ready"] as UploadStep[]).map((step) => (
                    <div
                      key={step}
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background:
                          uploadStep === step
                            ? "var(--accent)"
                            : uploadStep === "ready" || (step === "uploading" && uploadStep === "analysing")
                            ? "var(--accent)"
                            : "var(--bg-3)",
                        transition: "background 0.3s",
                        boxShadow:
                          uploadStep === step ? "0 0 6px var(--accent)" : "none",
                      }}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <>
                <UploadIcon />
                <p
                  style={{
                    color: "var(--text-2)",
                    fontSize: "0.88rem",
                    marginBottom: 4,
                  }}
                >
                  {isDragActive ? "Drop to upload" : "Drag a CSV file here"}
                </p>
                <p
                  style={{
                    color: "var(--text-3)",
                    fontSize: "0.8rem",
                    marginBottom: 20,
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  Max 50 MB · .csv only
                </p>
                <button className="btn btn-primary" onClick={open}>
                  Browse files
                </button>
              </>
            )}
          </div>

          {/* Error message */}
          {errorMessage && (
            <div
              style={{
                marginTop: 12,
                padding: "10px 14px",
                borderRadius: 6,
                background: "rgba(239,68,68,0.08)",
                border: "1px solid rgba(239,68,68,0.2)",
                color: "#EF4444",
                fontSize: "0.82rem",
                fontFamily: "var(--font-mono)",
              }}
            >
              {errorMessage}
            </div>
          )}

          {/* Bottom stats strip */}
          <div
            style={{
              display: "flex",
              gap: 28,
              marginTop: 32,
              paddingTop: 24,
              borderTop: "1px solid var(--border)",
            }}
          >
            {STATS.map(({ value, label }) => (
              <div key={label}>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontWeight: 600,
                    fontSize: "1.05rem",
                    color: "var(--text)",
                    letterSpacing: "-0.02em",
                  }}
                >
                  {value}
                </div>
                <div className="label" style={{ marginTop: 2 }}>
                  {label}
                </div>
              </div>
            ))}
          </div>

          {/* Feature grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 10,
              marginTop: 24,
            }}
          >
            {FEATURES.map(({ icon, title, desc }) => (
              <div
                key={title}
                className="panel"
                style={{ padding: "14px 16px", display: "flex", gap: 12, alignItems: "flex-start" }}
              >
                <span style={{ fontSize: 16, lineHeight: 1 }}>{icon}</span>
                <div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 11,
                      color: "var(--text)",
                      fontWeight: 500,
                      marginBottom: 3,
                    }}
                  >
                    {title}
                  </div>
                  <div style={{ color: "var(--text-3)", fontSize: "0.78rem", lineHeight: 1.5 }}>
                    {desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
