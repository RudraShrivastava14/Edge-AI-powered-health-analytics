# Figures

Plots and screenshots referenced by the root README, the report, and the slide deck.

## Generated figures (committed)

| File | What it shows | Real or mockup? |
|---|---|---|
| `sim_ecg_profiles.png` | Synthesised ECG for four profiles with the edge verdict on each | **Real** — output of `edge/simulator/generator.py` + `policy.py` |
| `sim_cascade_timeline.png` | Reconstruction error over a 400-window run against τ_low/τ_high, plus per-window uplink volume | **Real** |
| `sim_bandwidth.png` | Measured uplink volume vs. the stream-everything baseline (86.8 % reduction) | **Real** |
| `dashboard_mockup.svg` / `.png` | Clinician dashboard design | **Mockup** — the frontend is task F-1, not yet built. The image is stamped `UI MOCKUP · NOT IMPLEMENTED` so it cannot be mistaken for a screenshot. |

### Regenerating

```bash
pip install numpy matplotlib cairosvg
python results/figures/make_figures.py     # the three real figures
python results/figures/make_mockup.py      # the SVG mockup
# optional: re-render the mockup PNG
python -c "import cairosvg; cairosvg.svg2png(url='results/figures/dashboard_mockup.svg', \
    write_to='results/figures/dashboard_mockup.png', scale=1.6)"
```

Both scripts are seeded (`SEED = 7`), so the figures are stable across runs.

> **Important:** these figures reflect the *placeholder* scorer in
> `edge/edge_inference/policy.score_window`, not the trained TFLite model. Re-run both
> scripts after task M-5 and update the captions in the root README — the 86.8 % figure will
> change, and the report must quote the post-training number.

## Naming convention for experiment figures

`<experiment-id>_<short-description>.png` — e.g. `E4_latency_cdf.png`,
`E1_confusion_matrix.png`, `E7_cost_explorer.png`.

## Requirements

- Labelled axes **with units**, a caption, and a stated sample size on every figure.
- Export at ≥ 200 DPI or as SVG — projector-legible.
- Keep the generating code committed. A plot nobody can regenerate cannot be corrected.
- Screenshots: crop tightly, and **redact AWS account IDs and ARNs** before committing.
- Severity is never encoded by colour alone — colour plus icon plus text label.

## Expected experiment figures (to come)

`E1_pr_curve`, `E1_confusion_matrix`, `E2_quantisation_delta`, `E3_cascade_matrix`,
`E3_recall_vs_uplink`, `E4_latency_cdf`, `E5_bandwidth_bar`, `E6_concurrency_timeline`,
`E7_cost_explorer`, `E8_replay_timeline`, plus real dashboard screenshots once F-1 lands.
