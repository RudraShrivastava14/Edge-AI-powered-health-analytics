import React, { useState } from "react";
import { signIn } from "../services/auth.js";

export default function Login({ onSignedIn }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [needNew, setNeedNew] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      onSignedIn(await signIn(email.trim(), password, needNew ? newPassword : undefined));
    } catch (x) {
      if (x.code === "NewPasswordRequired") setNeedNew(true);
      setErr(x.message || "Sign-in failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="center">
      <form className="card narrow" onSubmit={submit}>
        <div className="brand big">
          <svg viewBox="0 0 32 32" width="34" height="34"><path d="M2 17h7l3-8 5 15 4-11 2 4h7" fill="none" stroke="#34d399" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <div><b>HealthEdge</b><small>Clinician dashboard</small></div>
        </div>
        <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required /></label>
        {needNew && (
          <label>New password<input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} autoComplete="new-password" minLength={10} required />
            <span className="muted tiny">At least 10 characters with upper case, lower case and a number.</span></label>
        )}
        {err && <div className="error">{err}</div>}
        <button className="primary" disabled={busy}>{busy ? "Signing in…" : needNew ? "Set password & sign in" : "Sign in"}</button>
      </form>
    </div>
  );
}
