"""
Data Processing Module for AutoInsight
- Session-scoped storage (no global state)
- Streaming CSV load with 50 MB hard limit
- Pandas summary stats, correlation, trend analysis
"""

import io
from typing import Any

import numpy as np
import pandas as pd
import structlog

from backend.modules import session_store as store

logger = structlog.get_logger(__name__)

MAX_FILE_BYTES = 50 * 1024 * 1024   # 50 MB hard limit
SAMPLE_ROWS    = 10_000              # cap for stats & LLM


# ── Ingestion ──────────────────────────────────────────────────────────────

def load_csv(file_bytes: bytes, filename: str, session_id: str) -> dict:
    """Parse CSV bytes, enforce size limit, sample large files, persist to session."""
    if len(file_bytes) > MAX_FILE_BYTES:
        raise ValueError(
            f"File too large ({len(file_bytes) / 1_048_576:.1f} MB). "
            f"Maximum allowed size is {MAX_FILE_BYTES // 1_048_576} MB."
        )

    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        if df.empty:
            raise ValueError("Uploaded CSV is empty.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not parse CSV: {exc}") from exc

    # Binary / non-text files produce single-column DataFrames with garbled headers
    if len(df.columns) == 1 and df.columns[0].startswith("\x00"):
        raise ValueError("Could not parse CSV: file appears to be binary, not text.")

    # Sanitise column names
    df.columns = [str(c).strip() for c in df.columns]

    original_rows = len(df)
    sampled = False
    if original_rows > SAMPLE_ROWS:
        df = df.sample(n=SAMPLE_ROWS, random_state=42).reset_index(drop=True)
        sampled = True

    # Store only what we need (serialise to JSON-safe dict)
    store.set_value(session_id, "df_json", df.to_json(orient="split"))
    store.set_value(session_id, "filename", filename)
    store.set_value(session_id, "original_rows", original_rows)

    logger.info(
        "csv_loaded",
        session_id=session_id,
        filename=filename,
        original_rows=original_rows,
        loaded_rows=len(df),
        sampled=sampled,
    )
    return {
        "session_id": session_id,
        "filename": filename,
        "original_rows": original_rows,
        "loaded_rows": len(df),
        "columns": list(df.columns),
        "sampled": sampled,
    }


def _get_df(session_id: str) -> pd.DataFrame:
    df_json = store.get_value(session_id, "df_json")
    if df_json is None:
        raise ValueError("No dataset found for this session. Please upload a CSV first.")
    return pd.read_json(io.StringIO(df_json), orient="split")


def get_metadata(session_id: str) -> dict:
    return {
        "filename": store.get_value(session_id, "filename"),
        "original_rows": store.get_value(session_id, "original_rows"),
    }


# ── Summary Statistics ─────────────────────────────────────────────────────

def compute_summary(session_id: str) -> dict:
    df = _get_df(session_id)

    numeric_cols     = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    # Numeric stats
    numeric_stats: dict = {}
    for col in numeric_cols:
        s = df[col]
        not_all_nan = not s.isna().all()
        numeric_stats[col] = {
            "mean":     round(float(s.mean()),   4) if not_all_nan else None,
            "median":   round(float(s.median()), 4) if not_all_nan else None,
            "std":      round(float(s.std()),    4) if not_all_nan else None,
            "min":      round(float(s.min()),    4) if not_all_nan else None,
            "max":      round(float(s.max()),    4) if not_all_nan else None,
            "missing":      int(s.isna().sum()),
            "missing_pct":  round(s.isna().mean() * 100, 2),
            "skewness": round(float(s.skew()),   4) if not_all_nan else None,
        }

    # Categorical stats
    categorical_stats: dict = {}
    for col in categorical_cols:
        vc = df[col].value_counts(dropna=False)
        categorical_stats[col] = {
            "unique":       int(df[col].nunique()),
            "missing":      int(df[col].isna().sum()),
            "missing_pct":  round(df[col].isna().mean() * 100, 2),
            "top_values":   {str(k): int(v) for k, v in vc.head(5).items()},
        }

    # Correlation matrix (up to 20 numeric cols)
    corr_matrix: dict = {}
    strong_corrs: list = []
    if len(numeric_cols) >= 2:
        corr_cols = numeric_cols[:20]
        corr = df[corr_cols].corr().round(3)
        corr_matrix = corr.to_dict()
        seen: set = set()
        for c1 in corr_matrix:
            for c2, val in corr_matrix[c1].items():
                if c1 != c2 and (c2, c1) not in seen and not np.isnan(val):
                    if abs(val) > 0.6:
                        strong_corrs.append({"col1": c1, "col2": c2, "r": val})
                        seen.add((c1, c2))

    # Trend detection — only meaningful if a datetime column orders the rows
    # Sort by first datetime col if present, otherwise use row order
    df_for_trends = df.copy()
    date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
    if not date_cols:
        # Try to parse object cols that look like dates
        for col in categorical_cols[:3]:
            try:
                parsed = pd.to_datetime(df[col], format="mixed", errors="coerce")
                if parsed.notna().mean() > 0.8:
                    df_for_trends = df_for_trends.sort_values(col).reset_index(drop=True)
                    break
            except Exception:
                pass

    trends: list = []
    for col in numeric_cols:
        s = df_for_trends[col].dropna()
        if len(s) < 10:
            continue
        window = max(2, len(s) // 10)
        rolling = s.rolling(window).mean().dropna()
        if len(rolling) < 2:
            continue
        mid = len(rolling) // 2
        first_half_mean  = rolling.iloc[:mid].mean()
        second_half_mean = rolling.iloc[mid:].mean()
        pct = (second_half_mean - first_half_mean) / (abs(first_half_mean) + 1e-9) * 100
        if abs(pct) > 10:
            trends.append({
                "column":        col,
                "direction":     "increasing" if pct > 0 else "decreasing",
                "magnitude_pct": round(float(pct), 2),
            })

    # Outlier detection — IQR method per numeric column
    outliers: dict = {}
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) < 4:
            continue
        q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((s < lower) | (s > upper)).sum())
        if n_out > 0:
            outliers[col] = {
                "count":       n_out,
                "pct":         round(n_out / len(s) * 100, 2),
                "lower_fence": round(lower, 4),
                "upper_fence": round(upper, 4),
            }

    # Data quality score: 0–100 (higher = cleaner)
    missing_penalty  = min(50, sum(v["missing_pct"] for v in numeric_stats.values()) / max(len(numeric_stats), 1))
    outlier_penalty  = min(30, sum(v["pct"] for v in outliers.values()) / max(len(outliers), 1))
    skew_penalty     = min(20, sum(abs(v["skewness"] or 0) for v in numeric_stats.values()) / max(len(numeric_stats), 1) * 2)
    data_quality_score = round(max(0, 100 - missing_penalty - outlier_penalty - skew_penalty), 1)

    return {
        "shape":               {"rows": len(df), "columns": len(df.columns)},
        "numeric_columns":     numeric_cols,
        "categorical_columns": categorical_cols,
        "numeric_stats":       numeric_stats,
        "categorical_stats":   categorical_stats,
        "correlation_matrix":  corr_matrix,
        "strong_correlations": strong_corrs,
        "trends":              trends,
        "outliers":            outliers,
        "data_quality_score":  data_quality_score,
        "missing_overview": {
            col: int(df[col].isna().sum())
            for col in df.columns if df[col].isna().any()
        },
    }


def get_preview(session_id: str, n: int = 50) -> list[dict]:
    df = _get_df(session_id)
    head = df.head(n)
    return head.where(pd.notnull(head), None).to_dict(orient="records")
