"use client";

import type { DataSummary, UploadMeta } from "@/lib/types";

interface KpiCardProps {
  value: string;
  label: string;
  color?: string;
  sublabel?: string;
  warn?: boolean;
}

export function KpiCard({ value, label, color, sublabel, warn }: KpiCardProps) {
  return (
    <div
      className="panel"
      style={{
        padding: "20px 24px",
        position: "relative",
        overflow: "hidden",
        transition: "border-color 0.2s",
      }}
    >
      {warn && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 2,
            background: "var(--warn)",
            borderRadius: "8px 8px 0 0",
          }}
        />
      )}
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontWeight: 700,
          fontSize: "1.75rem",
          color: color ?? "var(--text)",
          letterSpacing: "-0.04em",
          lineHeight: 1,
          marginBottom: 8,
        }}
      >
        {value}
      </div>
      <div className="label">{label}</div>
      {sublabel && (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            color: "var(--text-3)",
            marginTop: 4,
          }}
        >
          {sublabel}
        </div>
      )}
    </div>
  );
}

interface DataQualityGaugeProps {
  score: number;
}

export function DataQualityGauge({ score }: DataQualityGaugeProps) {
  const color =
    score >= 80 ? "var(--accent)" : score >= 50 ? "var(--warn)" : "var(--danger)";
  const label = score >= 80 ? "Good" : score >= 50 ? "Fair" : "Poor";

  return (
    <div
      className="panel"
      style={{ padding: "20px 24px", position: "relative", overflow: "hidden" }}
    >
      <div className="label" style={{ marginBottom: 12 }}>
        Data Quality Score
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, marginBottom: 12 }}>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontWeight: 700,
            fontSize: "1.75rem",
            color,
            letterSpacing: "-0.04em",
            lineHeight: 1,
          }}
        >
          {score}
        </span>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: "var(--text-3)",
            marginBottom: 4,
          }}
        >
          / 100
        </span>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            color,
            background: `${color}18`,
            padding: "2px 8px",
            borderRadius: 4,
            marginBottom: 4,
          }}
        >
          {label}
        </span>
      </div>
      <div
        style={{
          height: 4,
          background: "var(--bg-3)",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${score}%`,
            height: "100%",
            background: color,
            borderRadius: 2,
            transition: "width 0.8s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
        />
      </div>
    </div>
  );
}

interface KpiRowProps {
  meta: UploadMeta;
  summary: DataSummary;
}

export function KpiRow({ meta, summary }: KpiRowProps) {
  const missingColCount = Object.keys(summary.missing_overview).length;
  const outlierColCount = Object.keys(summary.outliers ?? {}).length;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(5, 1fr)",
        gap: 12,
      }}
    >
      <KpiCard
        value={meta.original_rows.toLocaleString()}
        label="Rows"
        color="var(--accent)"
        sublabel={meta.sampled ? "sampled to 10k" : undefined}
      />
      <KpiCard
        value={String(meta.columns.length)}
        label="Columns"
        color="var(--accent-2)"
      />
      <KpiCard
        value={String(summary.numeric_columns.length)}
        label="Numeric"
        color="var(--warn)"
      />
      <KpiCard
        value={String(missingColCount)}
        label="Missing cols"
        color={missingColCount > 0 ? "var(--warn)" : "var(--text-2)"}
        warn={missingColCount > 0}
      />
      <KpiCard
        value={String(outlierColCount)}
        label="Outlier cols"
        color={outlierColCount > 0 ? "var(--danger)" : "var(--text-2)"}
        warn={outlierColCount > 0}
      />
    </div>
  );
}
