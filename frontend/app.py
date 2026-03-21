"""
AutoInsight – Streamlit Frontend
Dark-themed data analysis dashboard.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api")

st.set_page_config(
    page_title="AutoInsight",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background-color: #0e0f1a; color: #e8e9f3; }
h1, h2, h3 { font-family: 'Space Mono', monospace; letter-spacing: -0.03em; }
.main-title { font-family:'Space Mono',monospace; font-size:2.6rem; font-weight:700;
  background:linear-gradient(135deg,#7c6af7,#4ecdc4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0; }
.subtitle { color:#7b7fa8; font-size:1.05rem; margin-top:.2rem; margin-bottom:2rem; }
.insight-card { background:linear-gradient(135deg,#16172d,#1c1e3a); border:1px solid #2a2d52;
  border-left:3px solid #7c6af7; border-radius:10px; padding:1rem 1.3rem; margin-bottom:.75rem; font-size:.95rem; line-height:1.6; }
.reason-card  { background:linear-gradient(135deg,#16172d,#1c1e3a); border:1px solid #2a2d52;
  border-left:3px solid #f7a26a; border-radius:10px; padding:1rem 1.3rem; margin-bottom:.75rem; font-size:.95rem; line-height:1.6; }
.action-card  { background:linear-gradient(135deg,#16172d,#1c1e3a); border:1px solid #2a2d52;
  border-left:3px solid #4ecdc4; border-radius:10px; padding:1rem 1.3rem; margin-bottom:.75rem; font-size:.95rem; line-height:1.6; }
.stat-box  { background:#16172d; border:1px solid #2a2d52; border-radius:10px; padding:1rem; text-align:center; }
.stat-value{ font-family:'Space Mono',monospace; font-size:1.6rem; font-weight:700; color:#7c6af7; }
.stat-label{ font-size:.8rem; color:#7b7fa8; margin-top:.2rem; }
.answer-box { background:#16172d; border:1px solid #2a2d52; border-radius:12px; padding:1.4rem; margin-top:1rem; }
.answer-text{ font-size:1.05rem; line-height:1.7; color:#e8e9f3; }
.badge-high   { display:inline-block; padding:.2rem .7rem; border-radius:20px; font-size:.75rem;
  font-family:'Space Mono',monospace; background:#1a3d2b; color:#4ecdc4; }
.badge-medium { display:inline-block; padding:.2rem .7rem; border-radius:20px; font-size:.75rem;
  font-family:'Space Mono',monospace; background:#3d2e1a; color:#f7a26a; }
.badge-low    { display:inline-block; padding:.2rem .7rem; border-radius:20px; font-size:.75rem;
  font-family:'Space Mono',monospace; background:#2d1a1a; color:#f77070; }
.section-header { font-family:'Space Mono',monospace; font-size:.75rem; letter-spacing:.15em;
  color:#7b7fa8; text-transform:uppercase; margin-bottom:1rem; padding-bottom:.5rem; border-bottom:1px solid #2a2d52; }
.stButton > button { background:linear-gradient(135deg,#7c6af7,#5d4fe0); color:white; border:none;
  border-radius:8px; padding:.6rem 1.5rem; font-family:'Space Mono',monospace; font-size:.85rem;
  font-weight:700; transition:all .2s; }
.stButton > button:hover { transform:translateY(-1px); box-shadow:0 6px 20px rgba(124,106,247,.4); }
</style>
""", unsafe_allow_html=True)


# ── API helpers ────────────────────────────────────────────────────────────

def _headers(session_id: str | None = None) -> dict:
    h = {}
    if session_id:
        h["X-Session-Id"] = session_id
    return h

def api_upload(file_bytes: bytes, filename: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/upload-data",
        files={"file": (filename, file_bytes, "text/csv")},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()

def api_analyze(session_id: str) -> dict:
    resp = requests.get(f"{API_BASE}/analyze", headers=_headers(session_id), timeout=30)
    resp.raise_for_status()
    return resp.json()

def api_insights(session_id: str) -> dict:
    resp = requests.post(f"{API_BASE}/generate-insights", headers=_headers(session_id), timeout=120)
    resp.raise_for_status()
    return resp.json()

def api_query(session_id: str, question: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/query",
        json={"question": question},
        headers=_headers(session_id),
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ── Session state init ─────────────────────────────────────────────────────

for key in ["session_id", "uploaded", "analysis", "insights"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ── Header ─────────────────────────────────────────────────────────────────

st.markdown('<p class="main-title">AutoInsight ✦</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Upload any dataset. Get instant AI-powered insights.</p>', unsafe_allow_html=True)
st.divider()


# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🗂 Upload Dataset")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file and st.button("⚡ Load & Analyze"):
        with st.spinner("Parsing dataset…"):
            try:
                meta = api_upload(uploaded_file.getvalue(), uploaded_file.name)
                session_id = meta["session_id"]
                analysis = api_analyze(session_id)
                st.session_state.session_id = session_id
                st.session_state.uploaded = meta
                st.session_state.analysis = analysis
                st.session_state.insights = None
                st.success(f"✓ Loaded {meta['loaded_rows']:,} rows × {len(meta['columns'])} columns")
            except requests.HTTPError as e:
                detail = e.response.json().get("detail", str(e)) if e.response else str(e)
                st.error(f"Upload failed: {detail}")
            except Exception as e:
                st.error(f"Upload failed: {e}")

    st.divider()

    if st.session_state.analysis:
        st.markdown("### 🤖 AI Insights")
        if st.button("🔮 Generate Insights"):
            with st.spinner("Thinking…"):
                try:
                    st.session_state.insights = api_insights(st.session_state.session_id)
                    cached = st.session_state.insights.pop("_cached", False)
                    if cached:
                        st.caption("⚡ Served from cache")
                except requests.HTTPError as e:
                    detail = e.response.json().get("detail", str(e)) if e.response else str(e)
                    st.error(f"Error: {detail}")

    st.divider()
    if st.session_state.session_id:
        st.caption(f"Session: `{st.session_state.session_id[:8]}…`")
    st.markdown(
        "<small style='color:#7b7fa8'>AutoInsight v1.1 · Powered by Claude</small>",
        unsafe_allow_html=True,
    )


# ── Main content ───────────────────────────────────────────────────────────

if not st.session_state.analysis:
    col1, col2, col3 = st.columns(3)
    features = [
        ("📊", "Summary Stats", "Mean, median, std, skewness, missing values — all computed instantly."),
        ("🔗", "Correlation Detection", "Automatically finds strong relationships between your variables."),
        ("✨", "AI Insights", "Claude reads your data summary and surfaces non-obvious patterns."),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3], features):
        with col:
            st.markdown(f"""
            <div class="stat-box" style="text-align:left;padding:1.5rem">
              <div style="font-size:2rem;margin-bottom:.5rem">{icon}</div>
              <div style="font-family:'Space Mono',monospace;font-weight:700;margin-bottom:.5rem">{title}</div>
              <div style="color:#7b7fa8;font-size:.9rem">{desc}</div>
            </div>""", unsafe_allow_html=True)
    st.stop()


# ── Dashboard ──────────────────────────────────────────────────────────────

analysis     = st.session_state.analysis
summary      = analysis["summary"]
preview_data = analysis["preview"]
m            = st.session_state.uploaded

col1, col2, col3, col4 = st.columns(4)
kpis = [
    ("Rows",          f"{m['original_rows']:,}"),
    ("Columns",       str(len(m["columns"]))),
    ("Numeric",       str(len(summary["numeric_columns"]))),
    ("Missing cols",  str(len(summary["missing_overview"]))),
]
for col, (label, val) in zip([col1, col2, col3, col4], kpis):
    with col:
        st.markdown(f'<div class="stat-box"><div class="stat-value">{val}</div>'
                    f'<div class="stat-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📋 Preview", "📈 Visualize", "🔬 Statistics", "💬 Ask a Question"])

PLOTLY_LAYOUT = dict(
    plot_bgcolor="#0e0f1a", paper_bgcolor="#0e0f1a",
    font_color="#e8e9f3", margin=dict(l=20, r=20, t=30, b=20),
)

# Tab 1
with tab1:
    st.markdown('<p class="section-header">Data Preview (first 50 rows)</p>', unsafe_allow_html=True)
    if preview_data:
        st.dataframe(pd.DataFrame(preview_data), use_container_width=True, height=400)

# Tab 2
with tab2:
    numeric_cols = summary["numeric_columns"]
    cat_cols     = summary["categorical_columns"]
    df_preview   = pd.DataFrame(preview_data)

    if not numeric_cols:
        st.info("No numeric columns found for visualisation.")
    else:
        vc1, vc2 = st.columns(2)
        with vc1:
            st.markdown('<p class="section-header">Distribution</p>', unsafe_allow_html=True)
            chosen = st.selectbox("Column", numeric_cols, key="dist_col")
            fig = px.histogram(df_preview, x=chosen, nbins=30,
                               color_discrete_sequence=["#7c6af7"], template="plotly_dark")
            fig.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

        with vc2:
            if len(numeric_cols) >= 2:
                st.markdown('<p class="section-header">Scatter Plot</p>', unsafe_allow_html=True)
                x_col = st.selectbox("X axis", numeric_cols, index=0, key="sx")
                y_col = st.selectbox("Y axis", numeric_cols, index=min(1, len(numeric_cols)-1), key="sy")
                color_col = st.selectbox("Color", ["None"] + cat_cols, key="sc")
                fig2 = px.scatter(df_preview, x=x_col, y=y_col,
                                  color=None if color_col == "None" else color_col,
                                  template="plotly_dark", opacity=0.7)
                fig2.update_layout(**PLOTLY_LAYOUT)
                st.plotly_chart(fig2, use_container_width=True)

        if len(numeric_cols) >= 2:
            st.markdown('<p class="section-header">Correlation Heatmap</p>', unsafe_allow_html=True)
            corr_dict = summary.get("correlation_matrix", {})
            if corr_dict:
                fig3 = px.imshow(pd.DataFrame(corr_dict), text_auto=".2f",
                                 color_continuous_scale="RdBu_r", template="plotly_dark", aspect="auto")
                fig3.update_layout(**PLOTLY_LAYOUT, height=400)
                st.plotly_chart(fig3, use_container_width=True)

        if cat_cols:
            st.markdown('<p class="section-header">Category Distribution</p>', unsafe_allow_html=True)
            chosen_cat = st.selectbox("Categorical column", cat_cols, key="cat")
            top_vals = summary["categorical_stats"][chosen_cat]["top_values"]
            fig4 = px.bar(x=list(top_vals.keys()), y=list(top_vals.values()),
                          color_discrete_sequence=["#4ecdc4"], template="plotly_dark",
                          labels={"x": chosen_cat, "y": "Count"})
            fig4.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig4, use_container_width=True)

# Tab 3
with tab3:
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown('<p class="section-header">Numeric Summary</p>', unsafe_allow_html=True)
        num_stats = summary.get("numeric_stats", {})
        if num_stats:
            rows = [{"Column": col, "Mean": s["mean"], "Median": s["median"], "Std": s["std"],
                     "Min": s["min"], "Max": s["max"], "Missing %": s["missing_pct"], "Skew": s["skewness"]}
                    for col, s in num_stats.items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with sc2:
        st.markdown('<p class="section-header">Strong Correlations</p>', unsafe_allow_html=True)
        strong = summary.get("strong_correlations", [])
        st.dataframe(pd.DataFrame(strong), use_container_width=True) if strong else st.info("No correlations |r| > 0.6 found.")

        st.markdown('<p class="section-header">Detected Trends</p>', unsafe_allow_html=True)
        trends = summary.get("trends", [])
        st.dataframe(pd.DataFrame(trends), use_container_width=True) if trends else st.info("No significant trends detected.")

    if st.session_state.insights:
        st.markdown('<p class="section-header">AI-Generated Insights</p>', unsafe_allow_html=True)
        ins = st.session_state.insights
        ic, rc, ac = st.columns(3)
        with ic:
            st.markdown("**🔍 Key Insights**")
            for item in ins.get("insights", []):
                st.markdown(f'<div class="insight-card">✦ {item}</div>', unsafe_allow_html=True)
        with rc:
            st.markdown("**🧩 Possible Reasons**")
            for item in ins.get("possible_reasons", []):
                st.markdown(f'<div class="reason-card">◈ {item}</div>', unsafe_allow_html=True)
        with ac:
            st.markdown("**🚀 Actionable Suggestions**")
            for item in ins.get("actionable_suggestions", []):
                st.markdown(f'<div class="action-card">→ {item}</div>', unsafe_allow_html=True)
    else:
        st.info("👈 Click Generate Insights in the sidebar for AI-powered analysis.")

# Tab 4
with tab4:
    st.markdown('<p class="section-header">Ask Anything About Your Data</p>', unsafe_allow_html=True)
    st.markdown("<p style='color:#7b7fa8;margin-bottom:1rem'>Ask questions in plain English.</p>",
                unsafe_allow_html=True)

    examples = ["Why are sales dropping?", "Which variables are most correlated?",
                "Are there data quality issues?", "What does the data suggest about customer behaviour?"]
    ecols = st.columns(len(examples))
    for col, ex in zip(ecols, examples):
        with col:
            if st.button(ex, key=f"ex_{ex[:8]}"):
                st.session_state["nl_q"] = ex

    question = st.text_input("Your question", value=st.session_state.get("nl_q", ""),
                              placeholder="e.g. What are the main drivers of churn?")

    if st.button("Ask AutoInsight 🔮") and question:
        with st.spinner("Analysing…"):
            try:
                result = api_query(st.session_state.session_id, question)
                conf = result.get("confidence", "medium")
                st.markdown(f"""
                <div class="answer-box">
                  <p style="color:#7b7fa8;font-size:.75rem;font-family:'Space Mono',monospace;
                     text-transform:uppercase;letter-spacing:.1em;margin-bottom:.5rem">
                    Answer <span class="badge-{conf}">Confidence: {conf}</span>
                  </p>
                  <p class="answer-text">{result.get('answer','')}</p>
                  {"<p style='color:#7b7fa8;font-size:.85rem;margin-top:.8rem'><em>⚠ " + result.get('caveat') + "</em></p>" if result.get('caveat') else ""}
                </div>""", unsafe_allow_html=True)
            except requests.HTTPError as e:
                detail = e.response.json().get("detail", str(e)) if e.response else str(e)
                st.error(f"Query failed: {detail}")
