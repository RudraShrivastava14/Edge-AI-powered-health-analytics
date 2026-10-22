import React from "react";
import { ago, FLAG_COLOR } from "../util.js";

export default function Devices({ devices, onPick }) {
  return (
    <section>
      <div className="title-row"><h1>Devices</h1></div>
      <div className="card">
        {devices.length === 0 ? <p className="muted">No devices have sent data yet.</p> : (
          <table className="tbl">
            <thead><tr><th>Device</th><th>Status</th><th>Last seen</th><th>Last HR</th><th>Last SpO₂</th><th>Last edge flag</th><th>Battery</th><th>Firmware</th><th /></tr></thead>
            <tbody>
              {devices.map((d) => (
                <tr key={d.deviceId}>
                  <td><b>{d.label || d.deviceId}</b>{d.label && d.label !== d.deviceId && <div className="muted tiny">{d.deviceId}</div>}</td>
                  <td><span className={`status ${d.status}`}>{d.status}</span></td>
                  <td>{d.lastSeen ? ago(d.lastSeen) : "—"}</td>
                  <td>{d.lastHr?.toFixed?.(0) ?? "—"} bpm</td>
                  <td>{d.lastSpo2?.toFixed?.(1) ?? "—"} %</td>
                  <td style={{ color: FLAG_COLOR[d.lastFlag] }}>{d.lastFlag || "—"}</td>
                  <td>{d.battery != null ? `${Math.round(d.battery * 100)} %` : "—"}</td>
                  <td>{d.fwVersion || "—"}</td>
                  <td><button className="small-btn" onClick={() => onPick(d.deviceId)}>View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
