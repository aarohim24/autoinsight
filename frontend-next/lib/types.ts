/**
 * Shared TypeScript types for AutoInsight.
 * Mirrors the response shapes produced by the FastAPI backend.
 */

export interface UploadMeta {
  session_id: string;
  filename: string;
  original_rows: number;
  loaded_rows: number;
  columns: string[];
  sampled: boolean;
}

export interface NumericStat {
  mean: number | null;
  median: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  missing_pct: number;
  skewness: number | null;
}

export interface CategoricalStat {
  unique: number;
  top_values: Record<string, number>;
  missing_pct: number;
}

export interface DataSummary {
  shape: { rows: number; columns: number };
  numeric_columns: string[];
  categorical_columns: string[];
  numeric_stats: Record<string, NumericStat>;
  categorical_stats: Record<string, CategoricalStat>;
  strong_correlations: { col1: string; col2: string; r: number }[];
  trends: { column: string; direction: string; magnitude_pct: number }[];
  missing_overview: Record<string, number>;
}

export interface AnalyzeResponse {
  meta: UploadMeta;
  summary: DataSummary;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  preview: Record<string, any>[];
}

export interface InsightResult {
  insights: string[];
  possible_reasons: string[];
  actionable_suggestions: string[];
}

export interface QueryResult {
  answer: string;
  confidence: "high" | "medium" | "low";
  caveat: string;
}
