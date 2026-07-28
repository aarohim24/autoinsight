"use client";

import { useState } from "react";
import type { InsightResult, DataSummary, QueryResult } from "@/lib/types";

// Matches the QueryEntry shape used in dashboard/page.tsx
interface QueryEntry {
  id: string;
  question: string;
  result: QueryResult;
  timestamp: Date;
}

interface ExportMenuProps {
  insights: InsightResult | null;
  summary: DataSummary | null;
  filename: string;
  queryHistory?: QueryEntry[];
}

export function ExportMenu({ insights, summary, filename, queryHistory = [] }: ExportMenuProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyInsights = async () => {
    if (!insights) return;
    const text = [
      `AutoInsight Report — ${filename}`,
      "",
      "## Key Findings",
      ...insights.insights.map((s) => `• ${s}`),
      "",
      "## Possible Reasons",
      ...insights.possible_reasons.map((s) => `• ${s}`),
      "",
      "## Actionable Suggestions",
      ...insights.actionable_suggestions.map((s) => `• ${s}`),
    ].join("\n");

    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    setOpen(false);
  };

  const downloadStatsCsv = () => {
    if (!summary) return;
    const rows: string[][] = [
      ["Column", "Mean", "Median", "Std", "Min", "Max", "Missing%", "Skewness"],
    ];
    for (const [col, s] of Object.entries(summary.numeric_stats)) {
      rows.push([
        col,
        String(s.mean ?? ""),
        String(s.median ?? ""),
        String(s.std ?? ""),
        String(s.min ?? ""),
        String(s.max ?? ""),
        String(s.missing_pct),
        String(s.skewness ?? ""),
      ]);
    }

    const csv = rows.map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename.replace(".csv", "")}_stats.csv`;
    a.click();
    URL.revokeObjectURL(url);
    setOpen(false);
  };

  const downloadConversationMd = () => {
    if (!queryHistory.length) return;
    const lines = [
      `# AutoInsight — Query Conversation`,
      `**File:** ${filename}`,
      `**Exported:** ${new Date().toLocaleString()}`,
      `**Questions:** ${queryHistory.length}`,
      "",
    ];
    queryHistory.forEach((entry, i) => {
      lines.push(
        `## Q${i + 1} — ${entry.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
        "",
        `**Question:** ${entry.question}`,
        "",
        `**Answer** *(confidence: ${entry.result.confidence})*`,
        "",
        entry.result.answer,
      );
      if (entry.result.caveat) {
        lines.push("", `> ⚠ ${entry.result.caveat}`);
      }
      lines.push("");
    });

    const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename.replace(".csv", "")}_conversation.md`;
    a.click();
    URL.revokeObjectURL(url);
    setOpen(false);
  };

  const downloadInsightsMd = () => {
    if (!insights) return;
    const md = [
      `# AutoInsight Report`,
      `**File:** ${filename}`,
      `**Generated:** ${new Date().toLocaleString()}`,
      "",
      "## Key Findings",
      ...insights.insights.map((s) => `- ${s}`),
      "",
      "## Possible Reasons",
      ...insights.possible_reasons.map((s) => `- ${s}`),
      "",
      "## Actionable Suggestions",
      ...insights.actionable_suggestions.map((s) => `- ${s}`),
    ].join("\n");

    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename.replace(".csv", "")}_insights.md`;
    a.click();
    URL.revokeObjectURL(url);
    setOpen(false);
  };

  const hasInsights = !!insights;
  const hasSummary = !!summary;
  const hasConversation = queryHistory.length > 0;

  return (
    <div style={{ position: "relative" }}>
      <button
        className="btn btn-secondary"
        onClick={() => setOpen((v) => !v)}
        style={{ fontSize: 11 }}
      >
        Export ▾
      </button>
      {open && (
        <>
          <div
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 49,
            }}
            onClick={() => setOpen(false)}
          />
          <div
            className="panel"
            style={{
              position: "absolute",
              right: 0,
              top: "calc(100% + 6px)",
              minWidth: 200,
              zIndex: 50,
              padding: "6px 0",
              boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
            }}
          >
            <ExportItem
              label={copied ? "✓ Copied!" : "Copy insights as text"}
              disabled={!hasInsights}
              onClick={copyInsights}
            />
            <ExportItem
              label="Download insights (.md)"
              disabled={!hasInsights}
              onClick={downloadInsightsMd}
            />
            <div
              style={{
                height: 1,
                background: "var(--border)",
                margin: "6px 0",
              }}
            />
            <ExportItem
              label="Download conversation (.md)"
              disabled={!hasConversation}
              onClick={downloadConversationMd}
            />
            <div
              style={{
                height: 1,
                background: "var(--border)",
                margin: "6px 0",
              }}
            />
            <ExportItem
              label="Download stats (.csv)"
              disabled={!hasSummary}
              onClick={downloadStatsCsv}
            />
          </div>
        </>
      )}
    </div>
  );
}

interface ExportItemProps {
  label: string;
  disabled?: boolean;
  onClick: () => void;
}

function ExportItem({ label, disabled, onClick }: ExportItemProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "block",
        width: "100%",
        textAlign: "left",
        background: "none",
        border: "none",
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color: disabled ? "var(--text-3)" : "var(--text-2)",
        padding: "8px 16px",
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "background 0.1s, color 0.1s",
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          (e.currentTarget as HTMLButtonElement).style.background = "var(--bg-3)";
          (e.currentTarget as HTMLButtonElement).style.color = "var(--text)";
        }
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLButtonElement).style.background = "none";
        (e.currentTarget as HTMLButtonElement).style.color = disabled
          ? "var(--text-3)"
          : "var(--text-2)";
      }}
    >
      {label}
    </button>
  );
}
