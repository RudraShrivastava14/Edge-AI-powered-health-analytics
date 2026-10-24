import React, { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from "recharts";
import { api } from "../services/api.js";
import { fmtTime, ago, FLAG_COLOR } from "../util.js";

const WINDOW_MIN = 30;

export default function LiveVitals({ deviceId, pollMs }) {
  const [latest, setLatest] = useState(null);
  const [series, setSeries] = useState([]);
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!deviceId) return;
    let stop = false;
    const load = async () => {
      try {
        const now = Date.now();
        const [l, v, s, a] = await Promise.all([
          api.latest(deviceId).catch((e) => (e.status === 404 ? null : Promise.reject(e))),
          api.allVitals(deviceId, now - WINDOW_MIN * 60000, now + 60000),
          api.stats(deviceId, 24),
          api.alerts("all", deviceId),
        ]);
        if (stop) return;
        setLatest(l); setSeries(v); setStats(s); setAlerts(a.items.slice(0, 6)); setErr("");
      } catch (e) { if (!stop) setErr(e.message); }
    };
    load();
    const t = setInterval(load, pollMs);
    return () => { stop = true; clearInterval(t); };
  }, [deviceId, pollMs]);

  if (!deviceId) return <Empty />;
  const f = latest?.flag || "normal";
  const sent = stats?.uplinkBytes || 0;
  // Baseline = zlib-compressed float32 ECG for every window, measured offline at ≈ 4.66 KB/window.
  const baseline = (stats?.windows || 0) * 4663;
  const reduction = baseline ? (1 - sent / baseline) * 100 : null;

  return (
    <section>
      <div className="title-row">
        <h1>Live vitals <span className="muted">— {deviceId}</span></h1>
        <span className="muted small">{latest ? `last window ${ago(latest.ts)} · refreshes every ${pollMs / 1000}s` : "waiting for data…"}</span>
      </div>
      {err && <div className="error">{err}</div>}
      <div className="tiles">
        <Tile label="Heart rate" value={latest?.hr?.toFixed(0)} unit="bpm" sub={latest ? `range ${latest.hrMin?.toFixed(0)}–${latest.hrMax?.toFixed(0)} · SDNN ${latest.sdnn?.toFixed(0)} ms` : ""} />
        <Tile label="SpO₂" value={latest?.spo2?.toFixed(1)} unit="%" warn={latest?.spo2 < 92} />
        <Tile label="Skin temp" value={latest?.tempC?.toFixed(1)} unit="°C" sub={latest ? `activity: ${latest.activity}` : ""} />
        <Tile label="Edge verdict" value={latest ? f.toUpperCase() : "—"} color={FLAG_COLOR[f]}
          sub={latest ? `${latest.modelVersion?.startsWith("edge-tiny") ? "P(abnormal)" : "score"} ${latest.reconError?.toFixed(3)} · ${latest.modelVersion || ""}${latest.cloudVerdict ? ` · cloud: ${latest.cloudVerdict}` : ""}` : ""} />
      </div>

      <div className="grid2">
        <div className="card">
          <h3>Heart rate — last {WINDOW_MIN} min</h3>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={series} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <defs><linearGradient id="hr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#60a5fa" stopOpacity={0.45} /><stop offset="1" stopColor="#60a5fa" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid stroke="#1f2a3a" vertical={false} />
              <XAxis dataKey="ts" tickFormatter={fmtTime} stroke="#64748b" fontSize={11} minTickGap={40} />
              <YAxis stroke="#64748b" fontSize={11} domain={[30, "auto"]} />
              <Tooltip content={<VitalTip />} />
              <ReferenceLine y={120} stroke="#f87171" strokeDasharray="4 4" />
              <ReferenceLine y={50} stroke="#fbbf24" strokeDasharray="4 4" />
              <Area type="monotone" dataKey="hr" stroke="#60a5fa" fill="url(#hr)" strokeWidth={2} dot={<FlagDot />} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
          <FlagStrip series={series} />
        </div>
        <div className="card">
          <h3>Recent alerts</h3>
          {alerts.length === 0 && <p className="muted">No alerts for this device.</p>}
          <ul className="alerts-mini">
            {alerts.map((a) => (
              <li key={a.alertId} className={`sev-${a.severity}`}>
                <b>{a.class.replaceAll("_", " ")}</b>
                <span className="muted small">{fmtTime(a.ts)} · {a.status}{a.notified === false ? " · debounced" : ""}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card">
        <h3>Edge → cloud efficiency (last 24 h)</h3>
        <div className="kpis">
          <Kpi label="Windows" value={stats?.windows ?? "—"} />
          <Kpi label="Normal / suspect / critical" value={stats ? `${stats.flags.normal} / ${stats.flags.suspect} / ${stats.flags.critical}` : "—"} />
          <Kpi label="Uplink sent" value={stats ? `${(sent / 1024).toFixed(1)} KB` : "—"} />
          <Kpi label="Stream-everything baseline" value={stats ? `${(baseline / 1024).toFixed(1)} KB` : "—"} />
          <Kpi label="Reduction" value={reduction != null ? `${reduction.toFixed(1)} %` : "—"} accent />
          <Kpi label="Edge → ingest p50 / p95" value={stats?.edgeToIngestMs?.p50 != null ? `${stats.edgeToIngestMs.p50} / ${stats.edgeToIngestMs.p95} ms` : "—"} />
        </div>
      </div>
    </section>
  );
}

function Tile({ label, value, unit, sub, color, warn }) {
  return (
    <div className="card tile">
      <div className="muted small upper">{label}</div>
      <div className="big" style={{ color: warn ? "#fbbf24" : color }}>{value ?? "—"}{value != null && unit && <span className="unit">{unit}</span>}</div>
      <div className="muted tiny">{sub}</div>
    </div>
  );
}

function Kpi({ label, value, accent }) {
  return <div className="kpi"><div className="muted tiny upper">{label}</div><div className={accent ? "kpi-v accent" : "kpi-v"}>{value}</div></div>;
}

function FlagDot({ cx, cy, payload }) {
  if (!payload || payload.flag === "normal") return null;
  return <circle cx={cx} cy={cy} r={4} fill={FLAG_COLOR[payload.flag]} stroke="#0b1220" />;
}

function FlagStrip({ series }) {
  if (!series.length) return null;
  return (
    <div className="strip" title="Edge verdict per 10-second window">
      {series.map((s) => <i key={s.ts} style={{ background: FLAG_COLOR[s.flag] }} />)}
    </div>
  );
}

function VitalTip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="tip">
      <b>{fmtTime(p.ts)}</b><br />HR {p.hr?.toFixed(1)} bpm · SpO₂ {p.spo2?.toFixed(1)}%<br />
      {p.activity} · <span style={{ color: FLAG_COLOR[p.flag] }}>{p.flag}</span>{p.cloudVerdict ? ` · cloud ${p.cloudVerdict}` : ""}
      {p.cloudReason && p.cloudVerdict === "rejected" ? <><br /><span className="muted">{p.cloudReason}</span></> : null}
    </div>
  );
}

function Empty() {
  return <section><div className="card"><h3>No devices yet</h3><p className="muted">Start the simulator — the device appears here after its first message.</p></div></section>;
}
