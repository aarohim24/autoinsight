"""
AutoInsight - Data Processing Module
Handles CSV ingestion, summary statistics, correlation, and trend analysis.
"""

import pandas as pd
import numpy as np
import io

MAX_ROWS_FOR_FULL_ANALYSIS = 10_000
SAMPLE_SIZE = 5_000


def load_csv(file_bytes: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
    return df


def sample_if_large(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) > MAX_ROWS_FOR_FULL_ANALYSIS:
        return df.sample(n=SAMPLE_SIZE, random_state=42)
    return df


def get_column_types(df: pd.DataFrame) -> dict:
    col_types = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            col_types[col] = "numeric"
        else:
            try:
                pd.to_datetime(df[col], infer_datetime_format=True)
                col_types[col] = "datetime"
            except Exception:
                col_types[col] = "categorical"
    return col_types


def compute_summary_stats(df: pd.DataFrame) -> dict:
    sample_df = sample_if_large(df)
    col_types = get_column_types(df)

    summary = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "sampled_rows": len(sample_df),
        "column_types": col_types,
        "missing_values": {},
        "numeric_stats": {},
        "categorical_stats": {},
        "correlations": [],
        "trends": {},
    }

    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        summary["missing_values"][col] = {
            "count": missing_count,
            "percentage": round(missing_count / len(df) * 100, 2),
        }

    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    if numeric_cols:
        desc = sample_df[numeric_cols].describe()
        for col in numeric_cols:
            try:
                summary["numeric_stats"][col] = {
                    "mean": round(float(desc[col]["mean"]), 4),
                    "median": round(float(sample_df[col].median()), 4),
                    "std": round(float(desc[col]["std"]), 4),
                    "min": round(float(desc[col]["min"]), 4),
                    "max": round(float(desc[col]["max"]), 4),
                    "q25": round(float(desc[col]["25%"]), 4),
                    "q75": round(float(desc[col]["75%"]), 4),
                    "skewness": round(float(sample_df[col].skew()), 4),
                }
            except Exception:
                pass

    cat_cols = [c for c, t in col_types.items() if t == "categorical"]
    for col in cat_cols:
        vc = sample_df[col].value_counts()
        summary["categorical_stats"][col] = {
            "unique_count": int(df[col].nunique()),
            "top_values": {str(k): int(v) for k, v in vc.head(5).items()},
        }

    if len(numeric_cols) >= 2:
        corr_matrix = sample_df[numeric_cols].corr()
        high_corr = []
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                val = corr_matrix.iloc[i, j]
                if not np.isnan(val):
                    high_corr.append({
                        "col_a": numeric_cols[i],
                        "col_b": numeric_cols[j],
                        "correlation": round(float(val), 4),
                    })
        high_corr.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        summary["correlations"] = high_corr[:10]

    if numeric_cols:
        col = numeric_cols[0]
        series = sample_df[col].dropna().reset_index(drop=True)
        if len(series) > 10:
            first_half_mean = float(series[: len(series) // 2].mean())
            second_half_mean = float(series[len(series) // 2 :].mean())
            change_pct = round((second_half_mean - first_half_mean) / (abs(first_half_mean) + 1e-9) * 100, 2)
            summary["trends"][col] = {
                "first_half_mean": round(first_half_mean, 4),
                "second_half_mean": round(second_half_mean, 4),
                "change_pct": change_pct,
                "direction": "increasing" if change_pct > 2 else "decreasing" if change_pct < -2 else "stable",
            }

    return summary


def get_chart_data(df: pd.DataFrame) -> dict:
    sample_df = sample_if_large(df)
    col_types = get_column_types(df)
    charts = {}
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]

    if numeric_cols:
        col = numeric_cols[0]
        series = sample_df[col].dropna()
        counts, bin_edges = np.histogram(series, bins=20)
        charts["histogram"] = {
            "column": col,
            "bins": [round(float(e), 4) for e in bin_edges[:-1]],
            "counts": [int(c) for c in counts],
        }

    if len(numeric_cols) >= 2:
        col_a, col_b = numeric_cols[0], numeric_cols[1]
        scatter_df = sample_df[[col_a, col_b]].dropna().head(500)
        charts["scatter"] = {
            "x_col": col_a,
            "y_col": col_b,
            "x": [round(float(v), 4) for v in scatter_df[col_a]],
            "y": [round(float(v), 4) for v in scatter_df[col_b]],
        }

    cat_cols = [c for c, t in col_types.items() if t == "categorical"]
    if cat_cols:
        col = cat_cols[0]
        vc = sample_df[col].value_counts().head(10)
        charts["bar"] = {
            "column": col,
            "labels": [str(k) for k in vc.index],
            "values": [int(v) for v in vc.values],
        }

    return charts


def build_llm_summary(df: pd.DataFrame, stats: dict) -> str:
    lines = []
    lines.append(f"Dataset: {stats['total_rows']} rows x {stats['total_columns']} columns.")
    if stats["sampled_rows"] < stats["total_rows"]:
        lines.append(f"(Analysis based on a {stats['sampled_rows']}-row sample)")

    lines.append("\n### Column Types")
    for col, t in stats["column_types"].items():
        lines.append(f"  - {col}: {t}")

    lines.append("\n### Missing Values")
    has_missing = False
    for col, mv in stats["missing_values"].items():
        if mv["count"] > 0:
            lines.append(f"  - {col}: {mv['count']} missing ({mv['percentage']}%)")
            has_missing = True
    if not has_missing:
        lines.append("  - No missing values detected")

    lines.append("\n### Numeric Column Statistics")
    for col, s in stats["numeric_stats"].items():
        lines.append(
            f"  - {col}: mean={s['mean']}, median={s['median']}, "
            f"std={s['std']}, min={s['min']}, max={s['max']}, skew={s['skewness']}"
        )

    lines.append("\n### Categorical Columns")
    for col, s in stats["categorical_stats"].items():
        top = ", ".join(f"{k}({v})" for k, v in list(s["top_values"].items())[:3])
        lines.append(f"  - {col}: {s['unique_count']} unique values. Top: {top}")

    if stats["correlations"]:
        lines.append("\n### Top Correlations")
        for c in stats["correlations"][:5]:
            lines.append(f"  - {c['col_a']} <-> {c['col_b']}: r={c['correlation']}")

    if stats["trends"]:
        lines.append("\n### Trend Analysis")
        for col, t in stats["trends"].items():
            lines.append(
                f"  - {col}: {t['direction']} ({t['change_pct']:+.1f}% from first half to second half)"
            )

    return "\n".join(lines)
