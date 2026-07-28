"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  generateInsights,
  askQuestion,
  getSessionStatus,
  deleteSession,
} from "@/lib/api";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

import type {
  UploadMeta,
  DataSummary,
  InsightResult,
  QueryResult,
} from "@/lib/types";

// ── Query history entry ───────────────────────────────────────────────────────

interface QueryEntry {
  id: string;
  question: string;
  result: QueryResult;
  timestamp: Date;
}

import { KpiRow, DataQualityGauge } from "@/components/KpiCard";
import { InsightColumn } from "@/components/InsightCard";
import { DashboardSkeleton, InsightSkeleton } from "@/components/LoadingSkeleton";
import { SessionExpiredBanner, SessionTtlBadge } from "@/components/SessionExpiredBanner";
import { ExportMenu } from "@/components/ExportMenu";

// ── Chart constants ──────────────────────────────────────────────────────────

const CHART_COLORS = ["#00FF87", "#0EA5E9", "#F59E0B", "#A78BFA", "#F472B6", "#34D399"];

const AXIS_PROPS = {
  stroke: "var(--text-3)",
  tick: { fontSize: 10, fontFamily: "var(--font-mono)", fill: "var(--text-3)" },
};

const GRID_PROPS = {
  strokeDasharray: "3 3",
  stroke: "rgba(255,255,255,0.04)",
};

// ── Custom chart tooltip ─────────────────────────────────────────────────────

interface TooltipPayloadItem {
  color?: string;
  name: string;
  value: number | string;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string | number;
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="panel" style={{ padding: "8px 12px", fontSize: 11, fontFamily: "var(--font-mono)" }}>
      {label !== undefined && (
        <p style={{ color: "var(--text-3)", marginBottom: 4 }}>{label}</p>
      )}
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color || "var(--accent)" }}>
          {entry.name}:{" "}
          {typeof entry.value === "number"
            ? entry.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
            : entry.value}
        </p>
      ))}
    </div>
  );
}

// ── Spinner ──────────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <svg
      className="spinner"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <circle cx="12" cy="12" r="10" strokeOpacity="0.2" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}

// ── Section heading ──────────────────────────────────────────────────────────

function SectionHeading({ title }: { title: string }) {
  return <p className="label" style={{ marginBottom: 16 }}>{title}</p>;
}

// ── Tab types ────────────────────────────────────────────────────────────────

type DashboardTab = "overview" | "charts" | "insights" | "ask";

const TABS: { id: DashboardTab; label: string }[] = [
  { id: "overview",  label: "Overview" },
  { id: "charts",    label: "Charts" },
  { id: "insights",  label: "Insights" },
  { id: "ask",       label: "Ask" },
];

// ── Dynamic suggested questions ──────────────────────────────────────────────
// Derived from the actual dataset so they are always relevant.

function buildSuggestedQuestions(
  summary: DataSummary | null,
  meta: UploadMeta | null
): string[] {
  if (!summary || !meta) return [];

  const questions: string[] = [];
  const numericCols      = summary.numeric_columns;
  const categoricalCols  = summary.categorical_columns;
  const trends           = summary.trends;
  const correlations     = summary.strong_correlations;
  const outlierCols      = Object.keys(summary.outliers ?? {});
  const missingCols      = Object.keys(summary.missing_overview ?? {});

  // Trend-based question (most specific — lead with it)
  if (trends.length > 0) {
    const t = trends[0];
    questions.push(
      `What is causing the ${t.direction} trend in ${t.column}?`
    );
  }

  // Correlation-based question
  if (correlations.length > 0) {
    const c = correlations[0];
    questions.push(`Why are ${c.col1} and ${c.col2} correlated?`);
  }

  // Cross-column aggregation (hardest NL case — showcases the system)
  if (numericCols.length >= 2) {
    questions.push(
      `Which ${categoricalCols[0] ?? "segment"} has the highest average ${numericCols[0]}?`
    );
  } else if (numericCols.length === 1) {
    questions.push(`What is the average ${numericCols[0]}?`);
  }

  // Outlier-based
  if (outlierCols.length > 0) {
    questions.push(`Explain the outliers in ${outlierCols[0]}.`);
  }

  // Missing data awareness
  if (missingCols.length > 0) {
    questions.push(
      `How does the missing data in ${missingCols[0]} affect the analysis?`
    );
  }

  // Fallback generic quality question
  questions.push("Are there any data quality issues I should be aware of?");

  // Return first 4, deduplicated
  return [...new Set(questions)].slice(0, 4);
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const router = useRouter();

  // Core data state
  const [uploadMeta, setUploadMeta]   = useState<UploadMeta | null>(null);
  const [dataSummary, setDataSummary] = useState<DataSummary | null>(null);
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([]);

  // UI state
  const [activeTab, setActiveTab] = useState<DashboardTab>("overview");
  const [isInitializing, setIsInitializing] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [sessionTtl, setSessionTtl] = useState<number | null>(null);

  // Insights state
  const [insights, setInsights]               = useState<InsightResult | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError]     = useState("");

  // Query state
  const [question, setQuestion]       = useState("");
  const [queryHistory, setQueryHistory] = useState<QueryEntry[]>([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const historyEndRef = useRef<HTMLDivElement>(null);

  // Chart column selectors
  const [selectedNumericCol, setSelectedNumericCol]     = useState(0);
  const [selectedCategoricalCol, setSelectedCategoricalCol] = useState(0);

  // ── Initialise from sessionStorage ────────────────────────────────────────

  useEffect(() => {
    const rawMeta     = sessionStorage.getItem("ai_meta");
    const rawAnalysis = sessionStorage.getItem("ai_analysis");

    if (!rawMeta || !rawAnalysis) {
      router.push("/");
      return;
    }

    const meta     = JSON.parse(rawMeta) as UploadMeta;
    const analysis = JSON.parse(rawAnalysis);

    setUploadMeta(meta);
    setDataSummary(analysis.summary);
    setPreviewRows(analysis.preview ?? []);
    setIsInitializing(false);

    // Fetch session TTL on mount
    getSessionStatus(meta.session_id)
      .then((status) => setSessionTtl(status.ttl_seconds))
      .catch(() => {
        // If 404 — session already expired
        setSessionExpired(true);
      });
  }, [router]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleGenerateInsights = async () => {
    if (!uploadMeta) return;
    setInsightsLoading(true);
    setInsightsError("");
    try {
      const result = await generateInsights(uploadMeta.session_id);
      setInsights(result);
      setActiveTab("insights");
    } catch (err: unknown) {
      setInsightsError((err as Error).message);
    } finally {
      setInsightsLoading(false);
    }
  };

  const handleAskQuestion = async () => {
    const q = question.trim();
    if (!uploadMeta || !q || queryLoading) return;
    setQueryLoading(true);
    setQuestion("");
    try {
      const result = await askQuestion(uploadMeta.session_id, q);
      setQueryHistory((prev) => [
        ...prev,
        { id: crypto.randomUUID(), question: q, result, timestamp: new Date() },
      ]);
    } catch (err: unknown) {
      setQueryHistory((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          question: q,
          result: { answer: (err as Error).message, confidence: "low", caveat: "" },
          timestamp: new Date(),
        },
      ]);
    } finally {
      setQueryLoading(false);
    }
  };

  // Auto-scroll conversation to latest entry
  useEffect(() => {
    historyEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [queryHistory]);

  const handleGoHome = useCallback(async () => {
    if (uploadMeta) {
      await deleteSession(uploadMeta.session_id).catch(() => {});
    }
    sessionStorage.clear();
    router.push("/");
  }, [uploadMeta, router]);

  const handleSessionExpired = useCallback(() => {
    setSessionExpired(true);
  }, []);

  // ── Derived chart data ─────────────────────────────────────────────────────

  const numericCols     = dataSummary?.numeric_columns ?? [];
  const categoricalCols = dataSummary?.categorical_columns ?? [];

  const activeNumericCol     = numericCols[selectedNumericCol] ?? numericCols[0];
  const activeCategoricalCol = categoricalCols[selectedCategoricalCol] ?? categoricalCols[0];

  const barChartData = previewRows.slice(0, 60).map((row, i) => ({
    i,
    value: typeof row[activeNumericCol] === "number" ? row[activeNumericCol] : 0,
  }));

  const categoryChartData = activeCategoricalCol
    ? Object.entries(
        dataSummary?.categorical_stats[activeCategoricalCol]?.top_values ?? {}
      ).map(([name, count]) => ({
        name: name === "null" ? "(null)" : name,
        value: count,
      }))
    : [];

  const scatterData =
    numericCols.length >= 2
      ? previewRows
          .slice(0, 120)
          .map((row) => ({ x: row[numericCols[0]], y: row[numericCols[1]] }))
          .filter((d) => d.x != null && d.y != null)
      : [];

  const lineChartData = previewRows.slice(0, 60).map((row, i) => ({
    i,
    ...numericCols.slice(0, 3).reduce(
      (acc, col) => ({ ...acc, [col]: row[col] }),
      {} as Record<string, unknown>
    ),
  }));

  const tabLabel = (id: DashboardTab) => {
    if (id === "insights" && insights) return `Insights (${insights.insights.length})`;
    return TABS.find((t) => t.id === id)?.label ?? id;
  };

  // ── Loading state ──────────────────────────────────────────────────────────

  if (isInitializing || !uploadMeta || !dataSummary) {
    return (
      <div style={{ minHeight: "100vh" }}>
        <div style={{ borderBottom: "1px solid var(--border)", height: 52 }} />
        <div className="container" style={{ padding: "28px 24px" }}>
          <DashboardSkeleton />
        </div>
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Session expired overlay */}
      {sessionExpired && <SessionExpiredBanner onGoHome={handleGoHome} />}

      {/* ── Header ── */}
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg)",
          position: "sticky",
          top: 0,
          zIndex: 50,
        }}
      >
        <div
          className="container"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            height: 52,
          }}
        >
          {/* Left side: back, filename, row count, sampled badge */}
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <button
              onClick={handleGoHome}
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--text-3)",
                background: "none",
                border: "none",
                cursor: "pointer",
                transition: "color 0.15s",
              }}
              onMouseEnter={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.color = "var(--text)")
              }
              onMouseLeave={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.color = "var(--text-3)")
              }
            >
              ← back
            </button>
            <div style={{ width: 1, height: 16, background: "var(--border)" }} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text)" }}>
              {uploadMeta.filename}
            </span>
            <span className="label">{uploadMeta.original_rows.toLocaleString()} rows</span>
            {uploadMeta.sampled && (
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  color: "var(--warn)",
                  background: "rgba(245,158,11,0.1)",
                  padding: "2px 7px",
                  borderRadius: 4,
                }}
              >
                sampled
              </span>
            )}
          </div>

          {/* Right side: TTL, export, generate insights */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <SessionTtlBadge ttlSeconds={sessionTtl} onExpired={handleSessionExpired} />
            <ExportMenu
              insights={insights}
              summary={dataSummary}
              filename={uploadMeta.filename}
              queryHistory={queryHistory}
            />
            <button
              className="btn btn-primary"
              onClick={handleGenerateInsights}
              disabled={insightsLoading}
              style={{ fontSize: 11 }}
            >
              {insightsLoading ? (
                <>
                  <Spinner /> Generating...
                </>
              ) : insights ? (
                "Regenerate"
              ) : (
                "Generate Insights"
              )}
            </button>
          </div>
        </div>

        {/* Tab bar */}
        <div className="container" style={{ display: "flex", gap: 4 }}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="btn btn-secondary"
              style={{
                borderRadius: "6px 6px 0 0",
                borderBottom: "none",
                fontSize: 11,
                padding: "7px 14px",
                ...(activeTab === tab.id
                  ? {
                      borderColor: "var(--accent)",
                      color: "var(--accent)",
                      background: "rgba(0,255,135,0.06)",
                    }
                  : {}),
              }}
            >
              {tabLabel(tab.id)}
            </button>
          ))}
        </div>
      </header>

      {/* ── Main content ── */}
      <main className="container" style={{ padding: "28px 24px", flex: 1 }}>

        {/* ── Overview tab ── */}
        {activeTab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* KPI row */}
            <KpiRow meta={uploadMeta} summary={dataSummary} />

            {/* Data quality + Correlations + Trends */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <DataQualityGauge score={dataSummary.data_quality_score} />

              {/* Correlations panel */}
              <div className="panel" style={{ padding: "20px 24px" }}>
                <SectionHeading title="Correlations" />
                {dataSummary.strong_correlations.length === 0 ? (
                  <p style={{ color: "var(--text-3)", fontSize: "0.82rem" }}>
                    No strong correlations found
                  </p>
                ) : (
                  dataSummary.strong_correlations.map((corr, i) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: 10,
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: 11,
                          color: "var(--text-2)",
                        }}
                      >
                        {corr.col1} / {corr.col2}
                      </span>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div
                          style={{
                            width: 64,
                            height: 3,
                            borderRadius: 2,
                            background: "var(--bg-3)",
                          }}
                        >
                          <div
                            style={{
                              width: `${Math.abs(corr.r) * 100}%`,
                              height: "100%",
                              background: corr.r > 0 ? "var(--accent)" : "var(--danger)",
                              borderRadius: 2,
                            }}
                          />
                        </div>
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: 11,
                            color: corr.r > 0 ? "var(--accent)" : "var(--danger)",
                            minWidth: 36,
                            textAlign: "right",
                          }}
                        >
                          {corr.r.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Trends panel */}
              <div className="panel" style={{ padding: "20px 24px" }}>
                <SectionHeading title="Trends" />
                {dataSummary.trends.length === 0 ? (
                  <p style={{ color: "var(--text-3)", fontSize: "0.82rem" }}>
                    No significant trends detected
                  </p>
                ) : (
                  dataSummary.trends.map((trend, i) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: 10,
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: 11,
                          color: "var(--text-2)",
                        }}
                      >
                        {trend.column}
                      </span>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: 11,
                          color:
                            trend.direction === "increasing"
                              ? "var(--accent)"
                              : "var(--danger)",
                        }}
                      >
                        {trend.direction === "increasing" ? "↑" : "↓"}{" "}
                        {Math.abs(trend.magnitude_pct).toFixed(1)}%
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Outliers panel (only if any exist) */}
            {Object.keys(dataSummary.outliers ?? {}).length > 0 && (
              <div className="panel" style={{ padding: "20px 24px" }}>
                <SectionHeading title="Outliers detected (IQR method)" />
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {Object.entries(dataSummary.outliers).map(([col, info]) => (
                    <div
                      key={col}
                      style={{
                        background: "rgba(239,68,68,0.06)",
                        border: "1px solid rgba(239,68,68,0.2)",
                        borderRadius: 6,
                        padding: "8px 14px",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      <span style={{ fontSize: 11, color: "var(--text-2)" }}>{col}</span>
                      <span
                        style={{
                          fontSize: 10,
                          color: "var(--danger)",
                          marginLeft: 8,
                        }}
                      >
                        {info.count} outliers ({info.pct}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Numeric stats table */}
            <div className="panel" style={{ padding: "20px 24px", overflowX: "auto" }}>
              <SectionHeading title="Numeric statistics" />
              <table className="data-table">
                <thead>
                  <tr>
                    {["Column", "Mean", "Median", "Std", "Min", "Max", "Missing%", "Skew"].map(
                      (h) => (
                        <th key={h}>{h}</th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {numericCols.map((col) => {
                    const stat = dataSummary.numeric_stats[col];
                    return (
                      <tr key={col}>
                        <td className="accent">{col}</td>
                        {[stat.mean, stat.median, stat.std, stat.min, stat.max].map(
                          (val, i) => (
                            <td key={i}>
                              {val?.toLocaleString(undefined, {
                                maximumFractionDigits: 2,
                              }) ?? "—"}
                            </td>
                          )
                        )}
                        <td className={stat.missing_pct > 5 ? "warn" : ""}>
                          {stat.missing_pct}%
                        </td>
                        <td className={Math.abs(stat.skewness ?? 0) > 1 ? "warn" : ""}>
                          {stat.skewness?.toFixed(2) ?? "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Data preview table */}
            <div className="panel" style={{ padding: "20px 24px", overflowX: "auto" }}>
              <SectionHeading
                title={`Preview — first ${Math.min(previewRows.length, 50)} rows`}
              />
              <table className="data-table">
                <thead>
                  <tr>
                    {uploadMeta.columns.map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewRows.slice(0, 50).map((row, i) => (
                    <tr key={i}>
                      {uploadMeta.columns.map((col) => (
                        <td
                          key={col}
                          style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis" }}
                        >
                          {(row[col] as React.ReactNode) ?? (
                            <span style={{ color: "var(--text-3)" }}>null</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Charts tab ── */}
        {activeTab === "charts" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Trend line chart */}
            {numericCols.length > 0 && (
              <div className="panel" style={{ padding: "20px 24px" }}>
                <SectionHeading title={`Trend — ${numericCols.slice(0, 3).join(", ")}`} />
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart
                    data={lineChartData}
                    margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid {...GRID_PROPS} />
                    <XAxis dataKey="i" hide />
                    <YAxis {...AXIS_PROPS} width={50} />
                    <Tooltip content={<ChartTooltip />} />
                    {numericCols.slice(0, 3).map((col, i) => (
                      <Line
                        key={col}
                        type="monotone"
                        dataKey={col}
                        stroke={CHART_COLORS[i]}
                        strokeWidth={1.5}
                        dot={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              {/* Distribution bar chart */}
              {numericCols.length > 0 && (
                <div className="panel" style={{ padding: "20px 24px" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 16,
                    }}
                  >
                    <SectionHeading title="Distribution" />
                    <select
                      value={selectedNumericCol}
                      onChange={(e) => setSelectedNumericCol(Number(e.target.value))}
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 11,
                        background: "var(--bg-3)",
                        color: "var(--text-2)",
                        border: "1px solid var(--border)",
                        borderRadius: 4,
                        padding: "4px 8px",
                        outline: "none",
                        cursor: "pointer",
                      }}
                    >
                      {numericCols.map((col, i) => (
                        <option key={col} value={i}>
                          {col}
                        </option>
                      ))}
                    </select>
                  </div>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart
                      data={barChartData}
                      margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
                      barSize={3}
                    >
                      <CartesianGrid {...GRID_PROPS} />
                      <XAxis dataKey="i" hide />
                      <YAxis {...AXIS_PROPS} width={50} />
                      <Tooltip content={<ChartTooltip />} />
                      <Bar dataKey="value" name={activeNumericCol} radius={[2, 2, 0, 0]}>
                        {barChartData.map((_, i) => (
                          <Cell
                            key={i}
                            fill={CHART_COLORS[i % CHART_COLORS.length]}
                            fillOpacity={0.7}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Category bar chart */}
              {categoricalCols.length > 0 && (
                <div className="panel" style={{ padding: "20px 24px" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 16,
                    }}
                  >
                    <SectionHeading title="Category distribution" />
                    <select
                      value={selectedCategoricalCol}
                      onChange={(e) =>
                        setSelectedCategoricalCol(Number(e.target.value))
                      }
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 11,
                        background: "var(--bg-3)",
                        color: "var(--text-2)",
                        border: "1px solid var(--border)",
                        borderRadius: 4,
                        padding: "4px 8px",
                        outline: "none",
                        cursor: "pointer",
                      }}
                    >
                      {categoricalCols.map((col, i) => (
                        <option key={col} value={i}>
                          {col}
                        </option>
                      ))}
                    </select>
                  </div>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart
                      data={categoryChartData}
                      layout="vertical"
                      margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid {...GRID_PROPS} horizontal={false} />
                      <XAxis type="number" {...AXIS_PROPS} />
                      <YAxis type="category" dataKey="name" width={80} {...AXIS_PROPS} />
                      <Tooltip content={<ChartTooltip />} />
                      <Bar dataKey="value" name="count" radius={[0, 2, 2, 0]}>
                        {categoryChartData.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Scatter plot */}
              {numericCols.length >= 2 && (
                <div
                  className="panel"
                  style={{ padding: "20px 24px", gridColumn: "span 2" }}
                >
                  <SectionHeading
                    title={`Scatter — ${numericCols[0]} vs ${numericCols[1]}`}
                  />
                  <ResponsiveContainer width="100%" height={200}>
                    <ScatterChart margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                      <CartesianGrid {...GRID_PROPS} />
                      <XAxis dataKey="x" name={numericCols[0]} {...AXIS_PROPS} />
                      <YAxis dataKey="y" name={numericCols[1]} {...AXIS_PROPS} width={50} />
                      <Tooltip
                        content={<ChartTooltip />}
                        cursor={{ strokeDasharray: "3 3", stroke: "var(--border-hi)" }}
                      />
                      <Scatter data={scatterData} fill="var(--accent)" fillOpacity={0.5} />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Insights tab ── */}
        {activeTab === "insights" && (
          <div>
            {!insights && !insightsLoading && (
              <div style={{ padding: "60px 0", textAlign: "center" }}>
                <p
                  style={{
                    color: "var(--text-3)",
                    fontSize: "0.85rem",
                    fontFamily: "var(--font-mono)",
                    marginBottom: 20,
                  }}
                >
                  No insights generated yet
                </p>
                <button
                  className="btn btn-primary"
                  onClick={handleGenerateInsights}
                >
                  Generate Insights
                </button>
                {insightsError && (
                  <p
                    style={{
                      color: "var(--danger)",
                      fontSize: "0.8rem",
                      marginTop: 12,
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {insightsError}
                  </p>
                )}
              </div>
            )}

            {insightsLoading && <InsightSkeleton />}

            {insights && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
                <InsightColumn
                  title="Key Findings"
                  items={insights.insights}
                  category="findings"
                  isCached={insights._cached}
                />
                <InsightColumn
                  title="Possible Reasons"
                  items={insights.possible_reasons}
                  category="reasons"
                />
                <InsightColumn
                  title="Next Steps"
                  items={insights.actionable_suggestions}
                  category="suggestions"
                />
              </div>
            )}
          </div>
        )}

        {/* ── Ask tab ── */}
        {activeTab === "ask" && (
          <div style={{ maxWidth: 680 }}>
            {/* Header row */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 4,
              }}
            >
              <SectionHeading title="Natural language query" />
              {queryHistory.length > 0 && (
                <button
                  className="btn btn-secondary"
                  onClick={() => setQueryHistory([])}
                  style={{ fontSize: 10, padding: "4px 10px" }}
                >
                  Clear history
                </button>
              )}
            </div>
            <p
              style={{
                color: "var(--text-3)",
                fontSize: "0.82rem",
                marginBottom: 20,
                lineHeight: 1.6,
              }}
            >
              Ask anything about your dataset in plain English. Each answer
              includes a confidence level and any caveats from the model.
            </p>

            {/* Suggestion chips — derived from the actual dataset */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
              {buildSuggestedQuestions(dataSummary, uploadMeta).map((q) => (
                <button
                  key={q}
                  className="btn btn-secondary"
                  onClick={() => setQuestion(q)}
                  style={{ fontSize: 11 }}
                  disabled={queryLoading}
                >
                  {q}
                </button>
              ))}
            </div>

            {/* Conversation history */}
            {queryHistory.length > 0 && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  marginBottom: 16,
                  maxHeight: 480,
                  overflowY: "auto",
                  paddingRight: 4,
                }}
              >
                {queryHistory.map((entry) => (
                  <div key={entry.id} className="fade-up">
                    {/* Question bubble */}
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "flex-end",
                        marginBottom: 6,
                      }}
                    >
                      <div
                        style={{
                          background: "rgba(0,255,135,0.07)",
                          border: "1px solid rgba(0,255,135,0.18)",
                          borderRadius: "8px 8px 2px 8px",
                          padding: "8px 14px",
                          maxWidth: "80%",
                          fontFamily: "var(--font-mono)",
                          fontSize: 12,
                          color: "var(--text)",
                          lineHeight: 1.5,
                        }}
                      >
                        {entry.question}
                      </div>
                    </div>

                    {/* Answer bubble */}
                    <div
                      className="panel"
                      style={{
                        padding: "14px 16px",
                        borderLeft: "2px solid",
                        borderLeftColor:
                          entry.result.confidence === "high"
                            ? "var(--accent)"
                            : entry.result.confidence === "medium"
                            ? "var(--warn)"
                            : "var(--danger)",
                      }}
                    >
                      {/* Confidence + timestamp row */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          marginBottom: 8,
                        }}
                      >
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: 10,
                            padding: "2px 8px",
                            borderRadius: 4,
                            background:
                              entry.result.confidence === "high"
                                ? "rgba(0,255,135,0.1)"
                                : entry.result.confidence === "medium"
                                ? "rgba(245,158,11,0.1)"
                                : "rgba(239,68,68,0.1)",
                            color:
                              entry.result.confidence === "high"
                                ? "var(--accent)"
                                : entry.result.confidence === "medium"
                                ? "var(--warn)"
                                : "var(--danger)",
                          }}
                        >
                          {entry.result.confidence} confidence
                        </span>
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: 9,
                            color: "var(--text-3)",
                            marginLeft: "auto",
                          }}
                        >
                          {entry.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>

                      {/* Answer text */}
                      <p
                        style={{
                          color: "var(--text-2)",
                          fontSize: "0.85rem",
                          lineHeight: 1.7,
                        }}
                      >
                        {entry.result.answer}
                      </p>

                      {/* Caveat */}
                      {entry.result.caveat && (
                        <p
                          style={{
                            color: "var(--text-3)",
                            fontSize: "0.78rem",
                            marginTop: 8,
                            fontStyle: "italic",
                            borderTop: "1px solid var(--border)",
                            paddingTop: 8,
                          }}
                        >
                          ⚠ {entry.result.caveat}
                        </p>
                      )}
                    </div>
                  </div>
                ))}

                {/* Thinking indicator */}
                {queryLoading && (
                  <div style={{ display: "flex", justifyContent: "flex-start" }}>
                    <div
                      className="panel"
                      style={{
                        padding: "12px 16px",
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        borderLeft: "2px solid var(--border-hi)",
                      }}
                    >
                      <Spinner />
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: 11,
                          color: "var(--text-3)",
                        }}
                      >
                        Thinking…
                      </span>
                    </div>
                  </div>
                )}

                <div ref={historyEndRef} />
              </div>
            )}

            {/* Thinking indicator when history is empty */}
            {queryLoading && queryHistory.length === 0 && (
              <div
                className="panel"
                style={{
                  padding: "14px 16px",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 16,
                  borderLeft: "2px solid var(--border-hi)",
                }}
              >
                <Spinner />
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    color: "var(--text-3)",
                  }}
                >
                  Thinking…
                </span>
              </div>
            )}

            {/* Input + Ask button */}
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) =>
                  e.key === "Enter" && !e.shiftKey && handleAskQuestion()
                }
                placeholder="Ask anything about your data…"
                disabled={queryLoading}
                style={{
                  flex: 1,
                  background: "var(--bg-2)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: "9px 14px",
                  color: "var(--text)",
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                  outline: "none",
                  transition: "border-color 0.15s, opacity 0.15s",
                  opacity: queryLoading ? 0.5 : 1,
                }}
                onFocus={(e) => (e.target.style.borderColor = "var(--border-hi)")}
                onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
              />
              <button
                className="btn btn-primary"
                onClick={handleAskQuestion}
                disabled={queryLoading || !question.trim()}
              >
                {queryLoading ? <Spinner /> : "Ask"}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
