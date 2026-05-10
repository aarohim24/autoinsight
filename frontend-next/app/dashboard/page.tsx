"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { generateInsights, askQuestion } from "@/lib/api";
import { BarChart, Bar, LineChart, Line, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

import type { UploadMeta, DataSummary, InsightResult, QueryResult } from "@/lib/types";

const C = ["#00FF87","#0EA5E9","#F59E0B","#A78BFA","#F472B6","#34D399"];
const AP = { stroke:"var(--text-3)", tick:{ fontSize:10, fontFamily:"var(--font-mono)", fill:"var(--text-3)" } };
const GP = { strokeDasharray:"3 3", stroke:"rgba(255,255,255,0.04)" };

const TT = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return <div className="panel" style={{ padding:"8px 12px", fontSize:11, fontFamily:"var(--font-mono)" }}>{label !== undefined && <p style={{ color:"var(--text-3)", marginBottom:4 }}>{label}</p>}{payload.map((p: any, i: number) => <p key={i} style={{ color:p.color||"var(--accent)" }}>{p.name}: {typeof p.value==="number" ? p.value.toLocaleString(undefined,{maximumFractionDigits:2}) : p.value}</p>)}</div>;
};

function SH({ title }: { title: string }) { return <p className="label" style={{ marginBottom:16 }}>{title}</p>; }
function Spin() { return <svg className="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" strokeOpacity="0.2"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>; }

export default function Dashboard() {
  const router = useRouter();
  const [meta, setMeta] = useState<UploadMeta | null>(null);
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [preview, setPreview] = useState<Record<string, any>[]>([]);
  const [insights, setInsights] = useState<InsightResult | null>(null);
  const [loadingI, setLoadingI] = useState(false);
  const [iErr, setIErr] = useState("");
  const [tab, setTab] = useState<"overview"|"charts"|"insights"|"ask">("overview");
  const [q, setQ] = useState("");
  const [ans, setAns] = useState<QueryResult | null>(null);
  const [loadingA, setLoadingA] = useState(false);
  const [sNum, setSNum] = useState(0);
  const [sCat, setSCat] = useState(0);

  useEffect(() => {
    const m = sessionStorage.getItem("ai_meta");
    const a = sessionStorage.getItem("ai_analysis");
    if (!m||!a) { router.push("/"); return; }
    setMeta(JSON.parse(m));
    const p = JSON.parse(a);
    setSummary(p.summary);
    setPreview(p.preview||[]);
  }, [router]);

  const doInsights = async () => {
    if (!meta) return;
    setLoadingI(true); setIErr("");
    try { const d = await generateInsights(meta.session_id); setInsights(d); setTab("insights"); }
    catch (e: any) { setIErr(e.message); }
    finally { setLoadingI(false); }
  };

  const doAsk = async () => {
    if (!meta||!q.trim()) return;
    setLoadingA(true); setAns(null);
    try { setAns(await askQuestion(meta.session_id, q)); }
    catch (e: any) { setAns({answer:e.message,confidence:"low",caveat:""}); }
    finally { setLoadingA(false); }
  };

  if (!meta||!summary) return <div style={{ height:"100vh", display:"flex", alignItems:"center", justifyContent:"center" }}><Spin /></div>;

  const nc = summary.numeric_columns;
  const cc = summary.categorical_columns;
  const cn = nc[sNum]||nc[0];
  const ccat = cc[sCat]||cc[0];
  const barD = preview.slice(0,60).map((r,i) => ({ i, v: typeof r[cn]==="number" ? r[cn] : 0 }));
  const catD = ccat ? Object.entries(summary.categorical_stats[ccat]?.top_values||{}).map(([k,v]) => ({ name:k==="null"?"null":k, value:v })) : [];
  const scD = nc.length>=2 ? preview.slice(0,120).map(r => ({ x:r[nc[0]], y:r[nc[1]] })).filter(d => d.x!=null&&d.y!=null) : [];
  const lineD = nc.length>0 ? preview.slice(0,60).map((r,i) => ({ i, ...nc.slice(0,3).reduce((a,c) => ({...a,[c]:r[c]}),{}) })) : [];

  const TABS = [{id:"overview",l:"Overview"},{id:"charts",l:"Charts"},{id:"insights",l:"Insights"+(insights?` (${insights.insights.length})` :"")},{id:"ask",l:"Ask"}] as const;

  const sel = (id: string) => ({ borderColor:"var(--accent)", color:"var(--accent)", background:"rgba(0,255,135,0.06)" });

  return (
    <div style={{ minHeight:"100vh", display:"flex", flexDirection:"column" }}>
      <header style={{ borderBottom:"1px solid var(--border)", background:"var(--bg)", position:"sticky", top:0, zIndex:50 }}>
        <div className="container" style={{ display:"flex", alignItems:"center", justifyContent:"space-between", height:52 }}>
          <div style={{ display:"flex", alignItems:"center", gap:16 }}>
            <button onClick={() => router.push("/")} style={{ fontFamily:"var(--font-mono)", fontSize:11, color:"var(--text-3)", background:"none", border:"none", cursor:"pointer" }}>← back</button>
            <div style={{ width:1, height:16, background:"var(--border)" }} />
            <span style={{ fontFamily:"var(--font-mono)", fontSize:13, color:"var(--text)" }}>{meta.filename}</span>
            <span className="label">{meta.original_rows.toLocaleString()} rows</span>
            {meta.sampled && <span style={{ fontFamily:"var(--font-mono)", fontSize:10, color:"var(--warn)", background:"rgba(245,158,11,0.1)", padding:"2px 7px", borderRadius:4 }}>sampled</span>}
          </div>
          <button className="btn btn-primary" onClick={doInsights} disabled={loadingI} style={{ fontSize:11 }}>
            {loadingI ? <><Spin /> Generating...</> : insights ? "Regenerate" : "Generate Insights"}
          </button>
        </div>
        <div className="container" style={{ display:"flex", gap:4 }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} className="btn btn-secondary" style={{ borderRadius:"6px 6px 0 0", borderBottom:"none", fontSize:11, padding:"7px 14px", ...(tab===t.id ? sel(t.id) : {}) }}>{t.l}</button>
          ))}
        </div>
      </header>

      <main className="container" style={{ padding:"28px 24px", flex:1 }}>

        {tab==="overview" && (
          <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
              {[{v:meta.original_rows.toLocaleString(),l:"Rows",c:"var(--accent)"},{v:String(meta.columns.length),l:"Columns",c:"var(--accent-2)"},{v:String(nc.length),l:"Numeric",c:"var(--warn)"},{v:String(Object.keys(summary.missing_overview).length),l:"Missing cols",c:Object.keys(summary.missing_overview).length>0?"var(--warn)":"var(--text-2)"}].map(({v,l,c}) => (
                <div key={l} className="panel" style={{ padding:"16px 20px" }}>
                  <div style={{ fontFamily:"var(--font-mono)", fontWeight:600, fontSize:"1.6rem", color:c, letterSpacing:"-0.03em", lineHeight:1 }}>{v}</div>
                  <div className="label" style={{ marginTop:6 }}>{l}</div>
                </div>
              ))}
            </div>

            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              <div className="panel" style={{ padding:"20px 24px" }}>
                <SH title="Correlations" />
                {summary.strong_correlations.length===0 ? <p style={{ color:"var(--text-3)", fontSize:"0.82rem" }}>No strong correlations found</p> :
                  summary.strong_correlations.map((c,i) => (
                    <div key={i} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10 }}>
                      <span style={{ fontFamily:"var(--font-mono)", fontSize:11, color:"var(--text-2)" }}>{c.col1} / {c.col2}</span>
                      <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                        <div style={{ width:64, height:3, borderRadius:2, background:"var(--bg-3)" }}>
                          <div style={{ width:`${Math.abs(c.r)*100}%`, height:"100%", background:c.r>0?"var(--accent)":"var(--danger)", borderRadius:2 }} />
                        </div>
                        <span style={{ fontFamily:"var(--font-mono)", fontSize:11, color:c.r>0?"var(--accent)":"var(--danger)", minWidth:36, textAlign:"right" }}>{c.r.toFixed(2)}</span>
                      </div>
                    </div>
                  ))
                }
              </div>
              <div className="panel" style={{ padding:"20px 24px" }}>
                <SH title="Trends" />
                {summary.trends.length===0 ? <p style={{ color:"var(--text-3)", fontSize:"0.82rem" }}>No significant trends detected</p> :
                  summary.trends.map((t,i) => (
                    <div key={i} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10 }}>
                      <span style={{ fontFamily:"var(--font-mono)", fontSize:11, color:"var(--text-2)" }}>{t.column}</span>
                      <span style={{ fontFamily:"var(--font-mono)", fontSize:11, color:t.direction==="increasing"?"var(--accent)":"var(--danger)" }}>{t.direction==="increasing"?"↑":"↓"} {Math.abs(t.magnitude_pct).toFixed(1)}%</span>
                    </div>
                  ))
                }
              </div>
            </div>

            <div className="panel" style={{ padding:"20px 24px", overflowX:"auto" }}>
              <SH title="Numeric statistics" />
              <table className="data-table">
                <thead><tr>{["Column","Mean","Median","Std","Min","Max","Missing","Skew"].map(h => <th key={h}>{h}</th>)}</tr></thead>
                <tbody>{nc.map(col => { const s=summary.numeric_stats[col]; return (
                  <tr key={col}>
                    <td className="accent">{col}</td>
                    {[s.mean,s.median,s.std,s.min,s.max].map((v,i) => <td key={i}>{v?.toLocaleString(undefined,{maximumFractionDigits:2})??"—"}</td>)}
                    <td className={s.missing_pct>5?"warn":""}>{s.missing_pct}%</td>
                    <td className={Math.abs(s.skewness??0)>1?"warn":""}>{s.skewness?.toFixed(2)??"—"}</td>
                  </tr>
                )})}</tbody>
              </table>
            </div>

            <div className="panel" style={{ padding:"20px 24px", overflowX:"auto" }}>
              <SH title={`Preview — first ${Math.min(preview.length,50)} rows`} />
              <table className="data-table">
                <thead><tr>{meta.columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>{preview.slice(0,50).map((row,i) => <tr key={i}>{meta.columns.map(c => <td key={c} style={{ maxWidth:160, overflow:"hidden", textOverflow:"ellipsis" }}>{row[c]??<span style={{ color:"var(--text-3)" }}>null</span>}</td>)}</tr>)}</tbody>
              </table>
            </div>
          </div>
        )}

        {tab==="charts" && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            {nc.length>0 && <div className="panel" style={{ padding:"20px 24px" }}>
              <SH title={`Trend — ${nc.slice(0,3).join(", ")}`} />
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={lineD} margin={{ top:4, right:4, left:0, bottom:0 }}>
                  <CartesianGrid {...GP} /><XAxis dataKey="i" hide /><YAxis {...AP} width={50} /><Tooltip content={<TT />} />
                  {nc.slice(0,3).map((c,i) => <Line key={c} type="monotone" dataKey={c} stroke={C[i]} strokeWidth={1.5} dot={false} />)}
                </LineChart>
              </ResponsiveContainer>
            </div>}
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
              {nc.length>0 && <div className="panel" style={{ padding:"20px 24px" }}>
                <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
                  <SH title="Distribution" />
                  <select value={sNum} onChange={e => setSNum(Number(e.target.value))} style={{ fontFamily:"var(--font-mono)", fontSize:11, background:"var(--bg-3)", color:"var(--text-2)", border:"1px solid var(--border)", borderRadius:4, padding:"4px 8px", outline:"none" }}>
                    {nc.map((c,i) => <option key={c} value={i}>{c}</option>)}
                  </select>
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={barD} margin={{ top:4, right:4, left:0, bottom:0 }} barSize={3}>
                    <CartesianGrid {...GP} /><XAxis dataKey="i" hide /><YAxis {...AP} width={50} /><Tooltip content={<TT />} />
                    <Bar dataKey="v" name={cn} radius={[2,2,0,0]}>{barD.map((_,i) => <Cell key={i} fill={C[i%C.length]} fillOpacity={0.7} />)}</Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>}
              {cc.length>0 && <div className="panel" style={{ padding:"20px 24px" }}>
                <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
                  <SH title="Category" />
                  <select value={sCat} onChange={e => setSCat(Number(e.target.value))} style={{ fontFamily:"var(--font-mono)", fontSize:11, background:"var(--bg-3)", color:"var(--text-2)", border:"1px solid var(--border)", borderRadius:4, padding:"4px 8px", outline:"none" }}>
                    {cc.map((c,i) => <option key={c} value={i}>{c}</option>)}
                  </select>
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={catD} layout="vertical" margin={{ top:4, right:4, left:0, bottom:0 }}>
                    <CartesianGrid {...GP} horizontal={false} /><XAxis type="number" {...AP} /><YAxis type="category" dataKey="name" width={80} {...AP} /><Tooltip content={<TT />} />
                    <Bar dataKey="value" name="count" radius={[0,2,2,0]}>{catD.map((_,i) => <Cell key={i} fill={C[i%C.length]} />)}</Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>}
              {nc.length>=2 && <div className="panel" style={{ padding:"20px 24px", gridColumn:"span 2" }}>
                <SH title={`Scatter — ${nc[0]} vs ${nc[1]}`} />
                <ResponsiveContainer width="100%" height={180}>
                  <ScatterChart margin={{ top:4, right:4, left:0, bottom:0 }}>
                    <CartesianGrid {...GP} /><XAxis dataKey="x" name={nc[0]} {...AP} /><YAxis dataKey="y" name={nc[1]} {...AP} width={50} /><Tooltip content={<TT />} cursor={{ strokeDasharray:"3 3", stroke:"var(--border-hi)" }} />
                    <Scatter data={scD} fill="var(--accent)" fillOpacity={0.5} />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>}
            </div>
          </div>
        )}

        {tab==="insights" && (
          <div>
            {!insights&&!loadingI && <div style={{ padding:"60px 0", textAlign:"center" }}>
              <p style={{ color:"var(--text-3)", fontSize:"0.85rem", fontFamily:"var(--font-mono)", marginBottom:20 }}>No insights generated yet</p>
              <button className="btn btn-primary" onClick={doInsights}>Generate Insights</button>
              {iErr && <p style={{ color:"var(--danger)", fontSize:"0.8rem", marginTop:12, fontFamily:"var(--font-mono)" }}>{iErr}</p>}
            </div>}
            {loadingI && <div style={{ padding:"60px 0", textAlign:"center", display:"flex", flexDirection:"column", alignItems:"center", gap:12 }}><Spin /><p style={{ color:"var(--text-3)", fontSize:"0.82rem", fontFamily:"var(--font-mono)" }}>Analysing dataset...</p></div>}
            {insights && <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:16 }}>
              {([{title:"Findings",items:insights.insights,accent:"var(--accent)"},{title:"Possible reasons",items:insights.possible_reasons,accent:"var(--warn)"},{title:"Next steps",items:insights.actionable_suggestions,accent:"var(--accent-2)"}] as const).map(({title,items,accent}) => (
                <div key={title}>
                  <SH title={title} />
                  {items.map((text,i) => (
                    <div key={i} className="panel fade-up" style={{ padding:"14px 16px", marginBottom:8, borderLeft:`2px solid ${accent}`, animationDelay:`${i*0.05}s`, opacity:0 }}>
                      <p style={{ color:"var(--text-2)", fontSize:"0.82rem", lineHeight:1.6 }}>{text}</p>
                    </div>
                  ))}
                </div>
              ))}
            </div>}
          </div>
        )}

        {tab==="ask" && (
          <div style={{ maxWidth:640 }}>
            <SH title="Natural language query" />
            <p style={{ color:"var(--text-3)", fontSize:"0.82rem", marginBottom:20 }}>Ask a question about your dataset in plain English.</p>
            <div style={{ display:"flex", flexWrap:"wrap", gap:8, marginBottom:16 }}>
              {["Why are sales dropping?","Which columns are correlated?","Any data quality issues?","What trends should I investigate?"].map(qs => (
                <button key={qs} className="btn btn-secondary" onClick={() => setQ(qs)} style={{ fontSize:11 }}>{qs}</button>
              ))}
            </div>
            <div style={{ display:"flex", gap:8, marginBottom:16 }}>
              <input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key==="Enter"&&doAsk()} placeholder="e.g. What is driving revenue growth?"
                style={{ flex:1, background:"var(--bg-2)", border:"1px solid var(--border)", borderRadius:6, padding:"9px 14px", color:"var(--text)", fontFamily:"var(--font-mono)", fontSize:12, outline:"none" }}
                onFocus={e => e.target.style.borderColor="var(--border-hi)"} onBlur={e => e.target.style.borderColor="var(--border)"} />
              <button className="btn btn-primary" onClick={doAsk} disabled={loadingA||!q.trim()}>{loadingA ? <Spin /> : "Run"}</button>
            </div>
            {ans && <div className="panel fade-up" style={{ padding:"18px 20px" }}>
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:12 }}>
                <span className="label">Response</span>
                <span style={{ fontFamily:"var(--font-mono)", fontSize:10, padding:"2px 8px", borderRadius:4, background:ans.confidence==="high"?"rgba(0,255,135,0.1)":ans.confidence==="medium"?"rgba(245,158,11,0.1)":"rgba(239,68,68,0.1)", color:ans.confidence==="high"?"var(--accent)":ans.confidence==="medium"?"var(--warn)":"var(--danger)" }}>{ans.confidence}</span>
              </div>
              <p style={{ color:"var(--text-2)", fontSize:"0.85rem", lineHeight:1.7 }}>{ans.answer}</p>
              {ans.caveat && <p style={{ color:"var(--text-3)", fontSize:"0.78rem", marginTop:10, fontStyle:"italic" }}>{ans.caveat}</p>}
            </div>}
          </div>
        )}
      </main>
    </div>
  );
}
