import React, { useEffect, useState } from "react";
import { initAuth, currentSession, signOut } from "./services/auth.js";
import { initApi, api } from "./services/api.js";
import Login from "./pages/Login.jsx";
import LiveVitals from "./pages/LiveVitals.jsx";
import Trends from "./pages/Trends.jsx";
import Alerts from "./pages/Alerts.jsx";
import Devices from "./pages/Devices.jsx";

const PAGES = [
  ["live", "Live vitals"],
  ["trends", "Trends"],
  ["alerts", "Alerts"],
  ["devices", "Devices"],
];

export default function App() {
  const [cfg, setCfg] = useState(null);
  const [cfgError, setCfgError] = useState(null);
  const [session, setSession] = useState(undefined);
  const [page, setPage] = useState(() => location.hash.slice(1) || "live");
  const [devices, setDevices] = useState([]);
  const [deviceId, setDeviceId] = useState(null);
  const [openAlerts, setOpenAlerts] = useState(0);

  useEffect(() => {
    fetch("/config.json", { cache: "no-store" })
      .then((r) => r.json())
      .then((c) => {
        if (!c.apiEndpoint || !c.userPoolId) throw new Error("config.json is not filled in yet");
        initAuth(c); initApi(c); setCfg(c);
        return currentSession();
      })
      .then((s) => setSession(s))
      .catch((e) => setCfgError(e.message));
  }, []);

  useEffect(() => { location.hash = page; }, [page]);

  useEffect(() => {
    if (!session) return;
    let stop = false;
    const load = async () => {
      try {
        const [d, a] = await Promise.all([api.devices(), api.alerts("open")]);
        if (stop) return;
        setDevices(d.devices);
        setDeviceId((cur) => cur || d.devices[0]?.deviceId || null);
        setOpenAlerts(a.items.length);
      } catch (e) {
        if (e.status === 401) { signOut(); setSession(null); }
      }
    };
    load();
    const t = setInterval(load, 15000);
    return () => { stop = true; clearInterval(t); };
  }, [session]);

  if (cfgError) return <div className="center"><div className="card narrow"><h2>Dashboard not configured</h2><p className="muted">{cfgError}</p></div></div>;
  if (!cfg || session === undefined) return <div className="center muted">Loading…</div>;
  if (!session) return <Login onSignedIn={setSession} />;

  const email = session.session.getIdToken().payload.email;
  const dev = devices.find((d) => d.deviceId === deviceId);
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <svg viewBox="0 0 32 32" width="26" height="26"><path d="M2 17h7l3-8 5 15 4-11 2 4h7" fill="none" stroke="#34d399" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <div><b>HealthEdge</b><small>Analytics platform</small></div>
        </div>
        <nav>
          {PAGES.map(([k, label]) => (
            <button key={k} className={page === k ? "active" : ""} onClick={() => setPage(k)}>
              {label}
              {k === "alerts" && openAlerts > 0 && <span className="pill red">{openAlerts}</span>}
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <div className="muted small">{email}</div>
          <button className="link" onClick={() => { signOut(); setSession(null); }}>Sign out</button>
          <div className="muted tiny">Academic prototype — not a medical device.</div>
        </div>
      </aside>
      <main>
        <header className="top">
          <div className="device-pick">
            <label className="muted small">Device</label>
            <select value={deviceId || ""} onChange={(e) => setDeviceId(e.target.value)}>
              {devices.length === 0 && <option value="">No devices yet</option>}
              {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label || d.deviceId}</option>)}
            </select>
            {dev && <span className={`status ${dev.status}`}>{dev.status}</span>}
          </div>
        </header>
        {page === "live" && <LiveVitals deviceId={deviceId} pollMs={cfg.pollMs || 5000} />}
        {page === "trends" && <Trends deviceId={deviceId} />}
        {page === "alerts" && <Alerts deviceId={deviceId} onChange={() => setOpenAlerts((n) => Math.max(0, n - 1))} />}
        {page === "devices" && <Devices devices={devices} onPick={(id) => { setDeviceId(id); setPage("live"); }} />}
      </main>
    </div>
  );
}
