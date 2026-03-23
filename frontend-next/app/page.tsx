"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { uploadCSV, analyze } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setLoading(true); setError(""); setStatus("Uploading...");
    try {
      const meta = await uploadCSV(file);
      setStatus("Analysing...");
      const analysis = await analyze(meta.session_id);
      sessionStorage.setItem("ai_meta", JSON.stringify(meta));
      sessionStorage.setItem("ai_analysis", JSON.stringify(analysis));
      router.push("/dashboard");
    } catch (e: any) { setError(e.message); setLoading(false); setStatus(""); }
  }, [router]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop, accept: { "text/csv": [".csv"] }, multiple: false, disabled: loading, noClick: true,
  });

  return (
    <main style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <nav style={{ borderBottom: "1px solid var(--border)", padding: "0 24px" }}>
        <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: 52 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, fontSize: 14, color: "var(--text)", letterSpacing: "-0.01em" }}>AutoInsight</span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div className="dot dot-green" />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-3)" }}>api ready</span>
          </div>
        </div>
      </nav>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "60px 24px" }}>
        <div style={{ width: "100%", maxWidth: 520 }}>
          <div style={{ marginBottom: 40 }}>
            <p className="label" style={{ marginBottom: 16 }}>Data Analysis Tool</p>
            <h1 style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: "2.2rem", lineHeight: 1.15, letterSpacing: "-0.03em", color: "var(--text)", marginBottom: 12 }}>
              From raw data<br />to clear answers.
            </h1>
            <p style={{ color: "var(--text-2)", fontSize: "0.95rem", lineHeight: 1.6 }}>
              Upload a CSV file to get summary statistics, charts, and AI-generated insights.
            </p>
          </div>
          <div {...getRootProps()} className="panel" style={{ padding: "36px 32px", textAlign: "center", borderStyle: "dashed", borderColor: isDragActive ? "var(--accent)" : "var(--border)", background: isDragActive ? "rgba(0,255,135,0.03)" : "var(--bg-2)", transition: "all 0.15s", cursor: "default" }}>
            <input {...getInputProps()} />
            {loading ? (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                <svg className="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" strokeOpacity="0.2"/><path d="M12 2a10 10 0 0 1 10 10"/>
                </svg>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-3)" }}>{status}</span>
              </div>
            ) : (
              <>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-3)" strokeWidth="1.5" style={{ margin: "0 auto 12px" }}>
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <p style={{ color: "var(--text-2)", fontSize: "0.88rem", marginBottom: 4 }}>{isDragActive ? "Drop to upload" : "Drag a CSV file here"}</p>
                <p style={{ color: "var(--text-3)", fontSize: "0.8rem", marginBottom: 20 }}>Max 50 MB</p>
                <button className="btn btn-primary" onClick={open}>Browse files</button>
              </>
            )}
          </div>
          {error && <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 6, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#EF4444", fontSize: "0.82rem", fontFamily: "var(--font-mono)" }}>{error}</div>}
          <div style={{ display: "flex", gap: 24, marginTop: 32, paddingTop: 24, borderTop: "1px solid var(--border)" }}>
            {[["CSV","Input format"],["50MB","Max size"],["83%","Test coverage"]].map(([v,l]) => (
              <div key={l}>
                <div style={{ fontFamily: "var(--font-mono)", fontWeight: 600, fontSize: "1rem", color: "var(--text)", letterSpacing: "-0.02em" }}>{v}</div>
                <div className="label" style={{ marginTop: 2 }}>{l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
