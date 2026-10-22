"""Render the proposed architecture diagram as a PNG.

The canonical, diffable source of the architecture is the Mermaid file in
``docs/architecture/diagrams/system-architecture.mmd`` — GitHub renders it inline. This
script produces a raster copy for the written report and the slide deck, where a Mermaid
block cannot be embedded.

    pip install numpy matplotlib
    python results/figures/make_architecture.py
"""

from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = pathlib.Path(__file__).resolve().parent

INK = "#1c2024"
MUTED = "#5b6672"
EDGE_C = "#2f7d68"
CLOUD_C = "#2563a8"
UI_C = "#8a4fa0"
DATA_C = "#c8850a"
ALERT_C = "#c0392b"

plt.rcParams.update({"font.size": 9, "figure.dpi": 200})


def box(ax, x, y, w, h, title, subtitle="", colour=CLOUD_C, fill="#ffffff", fs=9.5):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
        linewidth=1.4, edgecolor=colour, facecolor=fill, zorder=3))
    if subtitle:
        ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="center", fontsize=fs,
                fontweight="bold", color=INK, zorder=4)
        ax.text(x + w / 2, y + (h - 0.34) / 2, subtitle, ha="center", va="center",
                fontsize=7.4, color=MUTED, zorder=4, linespacing=1.4)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fs,
                fontweight="bold", color=INK, zorder=4)


def cylinder(ax, x, y, w, h, title, subtitle="", colour=DATA_C):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.16",
        linewidth=1.4, edgecolor=colour, facecolor="#fffaf0", zorder=3))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="center",
            fontsize=9.5, fontweight="bold", color=INK, zorder=4)
    if subtitle:
        ax.text(x + w / 2, y + (h - 0.34) / 2, subtitle, ha="center", va="center",
                fontsize=7.4, color=MUTED, zorder=4, linespacing=1.4)


def arrow(ax, p1, p2, colour=MUTED, style="-|>", label="", dashed=False, rad=0.0,
          lw=1.3, label_off=(0, 0.13), fs=7.2):
    ax.add_patch(FancyArrowPatch(
        p1, p2, arrowstyle=style, mutation_scale=11, linewidth=lw, color=colour,
        linestyle="--" if dashed else "-",
        connectionstyle=f"arc3,rad={rad}", zorder=2,
        shrinkA=2, shrinkB=2))
    if label:
        mx, my = (p1[0] + p2[0]) / 2 + label_off[0], (p1[1] + p2[1]) / 2 + label_off[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=fs, color=colour,
                zorder=5, bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none",
                                    alpha=0.9))


def tier(ax, x, y, w, h, label, colour):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.10",
        linewidth=1.2, edgecolor=colour, facecolor=colour, alpha=0.05, zorder=1))
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.10",
        linewidth=1.2, edgecolor=colour, facecolor="none", zorder=1))
    ax.text(x + 0.12, y + h - 0.18, label, ha="left", va="center", fontsize=10.5,
            fontweight="bold", color=colour, zorder=5)


def main() -> None:
    fig, ax = plt.subplots(figsize=(14.5, 7.6))
    ax.set_xlim(0, 15.6)
    ax.set_ylim(0, 8.1)
    ax.axis("off")

    # ---------------- tiers ----------------
    tier(ax, 0.15, 0.5, 3.45, 7.1, "EDGE TIER", EDGE_C)
    tier(ax, 3.85, 0.5, 8.05, 7.1, "AWS CLOUD TIER  ·  Free Tier, serverless", CLOUD_C)
    tier(ax, 12.15, 0.5, 3.3, 7.1, "PRESENTATION TIER", UI_C)

    # ---------------- edge ----------------
    box(ax, 0.4, 5.85, 2.95, 0.95, "Wearable Sensors",
        "ECG · PPG-HR · SpO₂ · Temp · IMU\n(or Python simulator)", EDGE_C, "#f2f9f6")
    box(ax, 0.4, 3.55, 2.95, 1.75, "Edge Gateway  (Raspberry Pi)",
        "① bandpass 0.5–40 Hz, resample 125 Hz\n"
        "② 10 s windows, 50 % overlap\n"
        "③ TFLite INT8 autoencoder (<500 KB)\n"
        "④ uplink policy: τ_low / τ_high\n"
        "⑤ store-and-forward SQLite buffer", EDGE_C, "#f2f9f6")
    box(ax, 0.4, 2.30, 2.95, 0.80, "Uplink decision",
        "normal → 430 B summary\nsuspect/critical → + waveform", ALERT_C, "#fdf3f2")

    arrow(ax, (1.88, 5.85), (1.88, 5.30), EDGE_C, label="BLE / serial", label_off=(0.62, 0))
    arrow(ax, (1.88, 3.55), (1.88, 3.10), EDGE_C)

    # ---------------- cloud ----------------
    box(ax, 4.05, 5.85, 2.35, 0.95, "AWS IoT Core",
        "MQTT/TLS 1.2 · X.509 per device\nRules Engine → Lambda", CLOUD_C, "#f1f6fb")
    box(ax, 4.05, 4.30, 2.35, 0.95, "λ  ingest_handler",
        "validate · normalise\nroute · archive", CLOUD_C, "#f1f6fb")
    box(ax, 4.05, 2.65, 2.35, 0.95, "λ  anomaly_processor",
        "full-precision confirmation\nmodel + rule cross-check", CLOUD_C, "#f1f6fb")
    box(ax, 4.05, 1.10, 2.35, 0.95, "λ  alert_dispatcher",
        "dedupe · debounce 5 min", CLOUD_C, "#f1f6fb")

    cylinder(ax, 6.95, 4.30, 2.25, 0.95, "Amazon DynamoDB",
             "Telemetry · Alerts · Devices\non-demand · TTL 30 d")
    cylinder(ax, 6.95, 5.85, 2.25, 0.95, "Amazon S3",
             "raw windows · models\nweb build · lifecycle → IA")
    box(ax, 6.95, 1.10, 2.25, 0.95, "Amazon SNS",
        "email / SMS to caregiver", ALERT_C, "#fdf3f2")

    box(ax, 9.70, 4.30, 2.00, 0.95, "λ  api_handler",
        "REST query layer", CLOUD_C, "#f1f6fb")
    box(ax, 9.70, 5.85, 2.00, 0.95, "API Gateway",
        "HTTP API\nJWT authorizer", CLOUD_C, "#f1f6fb")
    box(ax, 9.70, 2.85, 2.00, 0.80, "Amazon Cognito",
        "user pool", CLOUD_C, "#f1f6fb")
    box(ax, 6.95, 2.85, 2.25, 0.60, "Amazon CloudWatch  ·  X-Ray",
        "", MUTED, "#f6f7f8", fs=8.2)

    # ---------------- presentation ----------------
    box(ax, 12.40, 5.85, 2.80, 0.95, "React Dashboard",
        "S3 + CloudFront\nlive vitals · trends · alerts", UI_C, "#faf5fc")
    box(ax, 12.40, 4.30, 2.80, 0.95, "Clinician / Caregiver",
        "browser · email · SMS", UI_C, "#faf5fc")

    # ---------------- flows ----------------
    arrow(ax, (3.35, 2.70), (4.05, 6.10), CLOUD_C, rad=-0.22, lw=1.6)
    ax.text(1.88, 1.70, "MQTT publish over TLS 1.2\nhh/v1/{deviceId}/telemetry",
            ha="center", va="center", fontsize=7.0, color=CLOUD_C, zorder=5,
            bbox=dict(boxstyle="round,pad=0.22", fc="#f1f6fb", ec=CLOUD_C, lw=0.8))
    arrow(ax, (5.22, 5.85), (5.22, 5.25), CLOUD_C, label="IoT Rule", label_off=(0.52, 0))
    arrow(ax, (6.40, 4.90), (6.95, 6.10), DATA_C, rad=0.22, label="raw window",
          label_off=(-0.05, 0.30), fs=6.8)
    arrow(ax, (6.40, 4.70), (6.95, 4.70), DATA_C, label="PutItem", label_off=(0, 0.16))
    arrow(ax, (5.22, 4.30), (5.22, 3.60), ALERT_C,
          label="flag = suspect\nor critical", label_off=(0.78, 0.02), fs=6.8)
    arrow(ax, (5.22, 2.65), (5.22, 2.05), ALERT_C, label="confirmed", label_off=(0.62, 0))
    arrow(ax, (6.40, 1.58), (6.95, 1.58), ALERT_C, label="Publish", label_off=(0, 0.16))
    arrow(ax, (6.40, 3.10), (6.95, 3.15), MUTED, rad=0.0, dashed=True)
    arrow(ax, (6.40, 2.95), (6.95, 3.05), MUTED, dashed=True)
    arrow(ax, (9.20, 1.40), (12.40, 4.30), ALERT_C, rad=0.38, lw=1.5)
    ax.text(11.35, 1.32, "alert to caregiver", ha="center", va="center", fontsize=7.2,
            color=ALERT_C, zorder=5,
            bbox=dict(boxstyle="round,pad=0.20", fc="#fdf3f2", ec=ALERT_C, lw=0.7))

    arrow(ax, (12.40, 6.32), (11.70, 6.32), UI_C, label="HTTPS\n+ JWT",
          label_off=(0, 0.34), fs=6.8)
    arrow(ax, (10.70, 5.85), (10.70, 5.25), CLOUD_C)
    arrow(ax, (9.70, 4.78), (9.20, 4.78), DATA_C, label="Query", label_off=(0, 0.16))
    arrow(ax, (11.70, 3.25), (11.70, 6.10), UI_C, dashed=True, rad=-0.30,
          label="authorise", label_off=(0.34, -0.55), fs=6.8)
    arrow(ax, (13.80, 5.85), (13.80, 5.25), UI_C)

    # ---------------- footer ----------------
    fig.text(0.5, 0.028,
             "Two-stage cascade: the edge screens every 10-second window and escalates only "
             "suspicious ones; the cloud confirms them.\n"
             "Every cloud component is serverless and sits inside the AWS Free Tier — "
             "no always-on servers, target monthly cost $0.",
             ha="center", fontsize=8.6, color=MUTED, linespacing=1.5)
    fig.text(0.5, 0.965,
             "Cloud-Based Wearable Health Analytics Platform using Edge–Cloud Intelligence "
             "— Proposed Architecture",
             ha="center", fontsize=13, fontweight="bold", color=INK)

    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(OUT / "architecture_diagram.png", bbox_inches="tight", facecolor="white")
    print("wrote architecture_diagram.png")


if __name__ == "__main__":
    main()
