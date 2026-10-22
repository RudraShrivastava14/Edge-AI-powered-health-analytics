"""Generate the dashboard UI mockup (SVG).

This is a **design mockup**, not a screenshot — the frontend is task F-1 and is not built
yet. The word MOCKUP is stamped into the image itself so it cannot be mistaken for a
working system if the file is copied out of the README.

The ECG trace inside the mockup is genuine output from ``edge/simulator/generator.py``,
so the waveform shown is the one the real pipeline would render.

    python results/figures/make_mockup.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "edge"))

from simulator.generator import generate_window  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
W, H = 1200, 720

C = {
    "bg": "#0f1419",
    "panel": "#171d24",
    "panel2": "#1d242d",
    "line": "#2a333d",
    "text": "#e6edf3",
    "muted": "#8b98a5",
    "accent": "#4a9eff",
    "ok": "#3fb27f",
    "warn": "#e0a33e",
    "crit": "#e5534b",
}


def ecg_path(profile: str, x: float, y: float, w: float, h: float, seed: int) -> str:
    """Build an SVG polyline from a real simulator window."""
    win = generate_window(profile, rng=np.random.default_rng(seed))
    sig = win.ecg[: int(len(win.ecg) * 0.6)]
    sig = sig - sig.mean()
    sig = sig / (np.abs(sig).max() or 1.0)
    xs = x + np.linspace(0, w, sig.size)
    ys = y + h / 2 - sig * (h / 2 * 0.82)
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(xs, ys))


def card(x, y, w, h, label, value, unit, colour, sub) -> str:
    return f"""
  <g>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{C['panel2']}" stroke="{C['line']}"/>
    <text x="{x + 18}" y="{y + 28}" fill="{C['muted']}" font-size="12" letter-spacing="0.8">{label}</text>
    <text x="{x + 18}" y="{y + 72}" fill="{colour}" font-size="40" font-weight="600">{value}<tspan
      font-size="16" fill="{C['muted']}" font-weight="400"> {unit}</tspan></text>
    <text x="{x + 18}" y="{y + 96}" fill="{C['muted']}" font-size="11">{sub}</text>
  </g>"""


def _icon(x, y, colour, kind) -> str:
    """Drawn as paths, not glyphs — font coverage for symbols is unreliable."""
    if kind == "warn":     # triangle
        return (f'<path d="M{x} {y + 11} L{x + 6.5} {y - 1} L{x + 13} {y + 11} Z" '
                f'fill="none" stroke="{colour}" stroke-width="1.6" stroke-linejoin="round"/>'
                f'<line x1="{x + 6.5}" y1="{y + 3}" x2="{x + 6.5}" y2="{y + 6.5}" '
                f'stroke="{colour}" stroke-width="1.6" stroke-linecap="round"/>'
                f'<circle cx="{x + 6.5}" cy="{y + 9}" r="0.9" fill="{colour}"/>')
    return (f'<path d="M{x} {y + 5} L{x + 4.5} {y + 10} L{x + 13} {y - 1}" fill="none" '
            f'stroke="{colour}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')


def alert_row(x, y, w, time, dev, cls, sev, colour, icon) -> str:
    return f"""
  <g>
    <rect x="{x}" y="{y}" width="{w}" height="46" rx="8" fill="{C['panel2']}" stroke="{C['line']}"/>
    <rect x="{x}" y="{y}" width="4" height="46" rx="2" fill="{colour}"/>
    {_icon(x + 18, y + 16, colour, icon)}
    <text x="{x + 44}" y="{y + 21}" fill="{C['text']}" font-size="13" font-weight="600">{cls}</text>
    <text x="{x + 44}" y="{y + 37}" fill="{C['muted']}" font-size="11">{dev} · {time}</text>
    <rect x="{x + w - 96}" y="{y + 14}" width="76" height="19" rx="9" fill="{colour}" opacity="0.16"/>
    <text x="{x + w - 58}" y="{y + 27}" fill="{colour}" font-size="10" font-weight="600"
      text-anchor="middle" letter-spacing="0.6">{sev}</text>
  </g>"""


def build() -> str:
    nav = [("Overview", False), ("Live Vitals", True), ("Trends", False),
           ("Alerts", False), ("Devices", False)]
    nav_svg = ""
    for i, (name, active) in enumerate(nav):
        yy = 108 + i * 40
        if active:
            nav_svg += (f'<rect x="12" y="{yy - 22}" width="176" height="34" rx="8" '
                        f'fill="{C["accent"]}" opacity="0.14"/>'
                        f'<rect x="12" y="{yy - 22}" width="3" height="34" rx="2" fill="{C["accent"]}"/>')
        nav_svg += (f'<text x="34" y="{yy}" fill="{C["accent"] if active else C["muted"]}" '
                    f'font-size="13" font-weight="{600 if active else 400}">{name}</text>')

    alerts = (
        alert_row(628, 470, 548, "14:22:07", "demo-001", "Tachycardia confirmed", "HIGH", C["crit"], "warn") +
        alert_row(628, 526, 548, "13:58:41", "demo-003", "SpO₂ desaturation", "MEDIUM", C["warn"], "warn") +
        alert_row(628, 582, 548, "11:04:19", "demo-001", "Irregular RR interval", "LOW", C["ok"], "ok")
    )

    # 24 h heart-rate trend: circadian dip + noise + a tachycardia episode that lines up
    # with the shaded band, so the chart is consistent with its own annotation.
    rng = np.random.default_rng(11)
    n = 49
    hr = 74 + 8 * np.sin(np.linspace(0, 2 * np.pi, n) - 1.2) + rng.normal(0, 2.4, n)
    hr[24:29] += np.array([18, 46, 52, 38, 14])          # the episode
    tx = 250 + np.arange(n) * 6.9
    ty = 646 - (hr - 40) * 1.45
    trend = " ".join(f"{a:.0f},{b:.0f}" for a, b in zip(tx, ty))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
  viewBox="0 0 {W} {H}" font-family="Inter, 'Segoe UI', system-ui, sans-serif">
  <rect width="{W}" height="{H}" fill="{C['bg']}"/>

  <!-- sidebar -->
  <rect x="0" y="0" width="200" height="{H}" fill="{C['panel']}"/>
  <circle cx="30" cy="38" r="9" fill="none" stroke="{C['accent']}" stroke-width="2"/>
  <path d="M22 38 L27 38 L29 32 L33 44 L35 38 L40 38" fill="none" stroke="{C['accent']}" stroke-width="1.8"
    stroke-linejoin="round" stroke-linecap="round"/>
  <text x="48" y="36" fill="{C['text']}" font-size="14" font-weight="600">HealthEdge</text>
  <text x="48" y="50" fill="{C['muted']}" font-size="10">Analytics Platform</text>
  <line x1="0" y1="72" x2="200" y2="72" stroke="{C['line']}"/>
  {nav_svg}
  <line x1="0" y1="{H - 72}" x2="200" y2="{H - 72}" stroke="{C['line']}"/>
  <circle cx="32" cy="{H - 40}" r="13" fill="{C['accent']}" opacity="0.2"/>
  <text x="32" y="{H - 36}" fill="{C['accent']}" font-size="11" text-anchor="middle" font-weight="600">DR</text>
  <text x="54" y="{H - 43}" fill="{C['text']}" font-size="12">Dr. R. Sharma</text>
  <text x="54" y="{H - 29}" fill="{C['muted']}" font-size="10">Clinician</text>

  <!-- header -->
  <text x="228" y="46" fill="{C['text']}" font-size="20" font-weight="600">Live Vitals — demo-001</text>
  <text x="228" y="66" fill="{C['muted']}" font-size="12">Ward A · Bed 3</text>
  <g>
    <rect x="452" y="30" width="74" height="22" rx="11" fill="{C['ok']}" opacity="0.16"/>
    <circle cx="466" cy="41" r="4" fill="{C['ok']}"/>
    <text x="476" y="45" fill="{C['ok']}" font-size="11" font-weight="600">ONLINE</text>
  </g>
  <text x="{W - 24}" y="40" fill="{C['muted']}" font-size="11" text-anchor="end">
    last update 3 s ago · edge model ae-int8-1.2.0</text>
  <text x="{W - 24}" y="58" fill="{C['muted']}" font-size="11" text-anchor="end">
    alert latency p95: 3.4 s</text>

  <!-- vitals cards -->
  {card(228, 92, 224, 118, "HEART RATE", "78", "bpm", C['ok'], "range 71–86 · SDNN 42 ms")}
  {card(468, 92, 224, 118, "SpO₂", "97.8", "%", C['ok'], "min 96.0 · normal")}
  {card(708, 92, 224, 118, "SKIN TEMP", "36.6", "°C", C['ok'], "stable · rest")}
  {card(948, 92, 228, 118, "EDGE VERDICT", "NORMAL", "", C['ok'], "error 0.021 · τ 0.030")}

  <!-- ECG panel -->
  <rect x="228" y="230" width="948" height="212" rx="10" fill="{C['panel2']}" stroke="{C['line']}"/>
  <text x="250" y="258" fill="{C['text']}" font-size="13" font-weight="600">
    Single-lead ECG — live window</text>
  <text x="250" y="276" fill="{C['muted']}" font-size="11">125 Hz · 10 s window · activity: rest</text>
  <g opacity="0.35">
    {''.join(f'<line x1="250" y1="{300 + i * 30}" x2="1154" y2="{300 + i * 30}" stroke="{C["line"]}"/>'
             for i in range(5))}
    {''.join(f'<line x1="{250 + i * 60}" y1="300" x2="{250 + i * 60}" y2="420" stroke="{C["line"]}"/>'
             for i in range(16))}
  </g>
  <polyline points="{ecg_path('healthy', 250, 300, 904, 120, 3)}"
    fill="none" stroke="{C['ok']}" stroke-width="1.5" stroke-linejoin="round"/>

  <!-- trend panel -->
  <rect x="228" y="462" width="376" height="212" rx="10" fill="{C['panel2']}" stroke="{C['line']}"/>
  <text x="250" y="490" fill="{C['text']}" font-size="13" font-weight="600">Heart rate — last 24 h</text>
  <g opacity="0.35">
    {''.join(f'<line x1="250" y1="{520 + i * 30}" x2="582" y2="{520 + i * 30}" stroke="{C["line"]}"/>'
             for i in range(5))}
  </g>
  <rect x="{tx[24]:.0f}" y="516" width="{tx[28] - tx[24]:.0f}" height="130" fill="{C['crit']}" opacity="0.13"/>
  <polyline points="{trend}" fill="none" stroke="{C['accent']}" stroke-width="1.8"
    stroke-linejoin="round"/>
  <text x="{(tx[24] + tx[28]) / 2:.0f}" y="660" fill="{C['crit']}" font-size="9"
    text-anchor="middle">episode</text>
  <text x="250" y="660" fill="{C['muted']}" font-size="10">00:00</text>
  <text x="582" y="660" fill="{C['muted']}" font-size="10" text-anchor="end">now</text>

  <!-- alerts -->
  <text x="628" y="446" fill="{C['text']}" font-size="13" font-weight="600">Alert timeline</text>
  <text x="1176" y="446" fill="{C['accent']}" font-size="11" text-anchor="end">view all</text>
  {alerts}

  <!-- MOCKUP stamp — do not remove; this image is not a screenshot -->
  <g opacity="0.85">
    <rect x="{W - 232}" y="{H - 42}" width="216" height="28" rx="6"
      fill="{C['warn']}" opacity="0.16" stroke="{C['warn']}" stroke-width="1"/>
    <text x="{W - 124}" y="{H - 23}" fill="{C['warn']}" font-size="11" font-weight="700"
      text-anchor="middle" letter-spacing="1.2">UI MOCKUP · NOT IMPLEMENTED</text>
  </g>
</svg>
"""


if __name__ == "__main__":
    path = OUT / "dashboard_mockup.svg"
    path.write_text(build())
    print(f"wrote {path.relative_to(REPO)}")
