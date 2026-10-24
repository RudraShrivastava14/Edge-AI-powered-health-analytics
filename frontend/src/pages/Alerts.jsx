import React, { useEffect, useState } from "react";
import { api } from "../services/api.js";
import { fmtDateTime } from "../util.js";

export default function Alerts({ deviceId, onChange }) {
  const [status, setStatus] = useState("open");
  const [scope, setScope] = useState("all");
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    api.alerts(status, scope === "device" ? deviceId : undefined)
      .then((r) => { setItems(r.items); setErr(""); })
      .catch((e) => setErr(e.message));
  }, [status, scope, deviceId, tick]);

  useEffect(() => { const t = setInterval(() => setTick((x) => x + 1), 10000); return () => clearInterval(t); }, []);

  const ack = async (a) => {
    const note = prompt(`Acknowledge ${a.class.replace("_", " ")} on ${a.deviceId}? Optional note:`, "reviewed");
    if (note === null) return;
    try { await api.ack(a.alertId, note); onChange?.(); setTick((x) => x + 1); } catch (e) { setErr(e.message); }
  };

  return (
    <section>
      <div className="title-row">
        <h1>Alert timeline</h1>
        <div className="row">
          <div className="seg">{["open", "acknowledged", "all"].map((s) => <button key={s} className={s === status ? "active" : ""} onClick={() => setStatus(s)}>{s}</button>)}</div>
          <div className="seg">{[["all", "All devices"], ["device", "This device"]].map(([s, l]) => <button key={s} className={s === scope ? "active" : ""} onClick={() => setScope(s)}>{l}</button>)}</div>
        </div>
      </div>
      {err && <div className="error">{err}</div>}
      <div className="card">
        {items.length === 0 ? <p className="muted">No {status === "all" ? "" : status} alerts.</p> : (
          <table className="tbl">
            <thead><tr><th>Time</th><th>Device</th><th>Class</th><th>Severity</th><th>HR / SpO₂</th><th>Cloud ML (beats)</th><th>Confidence</th><th>Notified</th><th>End-to-end</th><th>Status</th><th /></tr></thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.alertId}>
                  <td>{fmtDateTime(a.ts)}</td>
                  <td>{a.deviceId}</td>
                  <td className="cap">{a.class.replaceAll("_", " ")}</td>
                  <td><span className={`pill sev-${a.severity}`}>{a.severity}</span></td>
                  <td>{a.hr?.toFixed?.(0)} bpm / {a.spo2?.toFixed?.(1)}%</td>
                  <td>{a.beats ? <span title={a.cloudModel}>{["V", "S"].filter((k) => a.abnormalBeats?.[k]).map((k) => `${a.abnormalBeats[k]} ${k}`).join(" · ") || "rules"} / {a.beats}</span> : "—"}</td>
                  <td>{a.confidence}</td>
                  <td>{a.notified ? "email sent" : a.notified === false ? "debounced" : "…"}</td>
                  <td>{a.endToEndMs != null ? `${(a.endToEndMs / 1000).toFixed(2)} s` : "—"}</td>
                  <td>{a.status === "acknowledged" ? <span title={a.ackNote}>ack by {a.ackBy?.split("@")[0]}</span> : "open"}</td>
                  <td>{a.status === "open" && <button className="small-btn" onClick={() => ack(a)}>Acknowledge</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
