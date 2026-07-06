"use client";

import { useState } from "react";

type InsightCategory = "findings" | "reasons" | "suggestions";

interface InsightCardProps {
  text: string;
  index: number;
  category: InsightCategory;
}

const CATEGORY_CONFIG: Record<
  InsightCategory,
  { accent: string; icon: string; label: string }
> = {
  findings: {
    accent: "var(--accent)",
    icon: "📊",
    label: "Finding",
  },
  reasons: {
    accent: "var(--warn)",
    icon: "🔍",
    label: "Reason",
  },
  suggestions: {
    accent: "var(--accent-2)",
    icon: "💡",
    label: "Action",
  },
};

export function InsightCard({ text, index, category }: InsightCardProps) {
  const [copied, setCopied] = useState(false);
  const config = CATEGORY_CONFIG[category];

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="panel fade-up"
      style={{
        padding: "14px 16px",
        marginBottom: 8,
        borderLeft: `2px solid ${config.accent}`,
        animationDelay: `${index * 0.06}s`,
        opacity: 0,
        position: "relative",
        cursor: "default",
        transition: "background 0.15s, border-color 0.15s",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.background = "var(--bg-3)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.background = "var(--bg-2)";
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <p
          style={{
            color: "var(--text-2)",
            fontSize: "0.82rem",
            lineHeight: 1.65,
            flex: 1,
          }}
        >
          {text}
        </p>
        <button
          onClick={handleCopy}
          title="Copy to clipboard"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: copied ? config.accent : "var(--text-3)",
            fontSize: 12,
            padding: "2px 4px",
            borderRadius: 4,
            flexShrink: 0,
            transition: "color 0.15s",
            fontFamily: "var(--font-mono)",
          }}
        >
          {copied ? "✓" : "⎘"}
        </button>
      </div>
    </div>
  );
}

interface InsightColumnProps {
  title: string;
  items: string[];
  category: InsightCategory;
  isCached?: boolean;
}

export function InsightColumn({ title, items, category, isCached }: InsightColumnProps) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <p className="label">{title}</p>
        {isCached && (
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 9,
              color: "var(--text-3)",
              background: "var(--bg-3)",
              padding: "2px 6px",
              borderRadius: 3,
              letterSpacing: "0.05em",
            }}
          >
            CACHED
          </span>
        )}
      </div>
      {items.map((text, i) => (
        <InsightCard
          key={i}
          text={text}
          index={i}
          category={category}
        />
      ))}
    </div>
  );
}
