import React, { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../services/api.js";
import { fmtTime, fmtDateTime } from "../util.js";

const RANGES = [["1h", 1], ["6h", 6], ["24h", 24], ["7d", 168]];

function bucket(items, hours) {
  // Down-sample to ~300 points so long ranges stay readable.
  const size = Math.max(1, Math.ceil(items.length / 300));
  if (size === 1) return items;
  const out = [];
  for (let i = 0; i < items.length; i += size) {
    const g = items.slice(i, i + size);
    const avg = (k) => g.reduce((s, x) => s + (x[k] ?? 0), 0) / g.length;
    out.push({ ts: g[0].ts, hr: avg("hr"), spo2: avg("spo2"), tempC: avg("tempC"), hrMax: Math.max(...g.map((x) => x.hrMax ?? 0)) });
  }
  return out;
}

export default function Trends({ deviceId }) {
  const [hours, setHours] = useState(6);
  const [data, setData] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!deviceId) return;
    setBusy(true);
    const now = Date.now();
    api.allVitals(deviceId, now - hours * 3600000, now + 60000)
      .then((v) => { setData(bucket(v, hours)); setErr(""); })
      .catch((e) => setErr(e.message))
      .finally(() => setBusy(false));
  }, [deviceId, hours]);

  const fmt = hours > 24 ? fmtDateTime : fmtTime;
  return (
    <section>
      <div className="title-row">
        <h1>Trends <span className="muted">— {deviceId}</span></h1>
        <div className="seg">{RANGES.map(([l, h]) => <button key={l} className={h === hours ? "active" : ""} onClick={() => setHours(h)}>{l}</button>)}</div>
      </div>
      {err && <div className="error">{err}</div>}
      {busy && <p className="muted">Loading…</p>}
      {!busy && data.length === 0 && <div className="card"><p className="muted">No data in this range.</p></div>}
      {data.length > 0 && (
        <>
          <Chart title="Heart rate (bpm)" data={data} k="hr" color="#60a5fa" fmt={fmt} domain={[30, "auto"]} />
          <Chart title="SpO₂ (%)" data={data} k="spo2" color="#34d399" fmt={fmt} domain={[80, 100]} />
          <Chart title="Skin temperature (°C)" data={data} k="tempC" color="#f472b6" fmt={fmt} domain={[35, 38.5]} />
        </>
      )}
    </section>
  );
}

function Chart({ title, data, k, color, fmt, domain }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="#1f2a3a" vertical={false} />
          <XAxis dataKey="ts" tickFormatter={fmt} stroke="#64748b" fontSize={11} minTickGap={50} />
          <YAxis stroke="#64748b" fontSize={11} domain={domain} />
          <Tooltip labelFormatter={fmtDateTime} formatter={(v) => v?.toFixed(1)} contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
          <Line type="monotone" dataKey={k} stroke={color} dot={false} strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
