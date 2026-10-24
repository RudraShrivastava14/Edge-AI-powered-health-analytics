"""Replay real MIT-BIH recordings as a live wearable stream.

Records are pre-converted by ai-models/preprocessing/export_replay.py into compact .npz files
(edge/data/mitbih/<record>.npz: 125 Hz ECG + cardiologist beat annotations). Each 10-second
slice becomes a Window exactly like the synthetic generator's, so the whole pipeline - edge
model, uplink, cloud classifier, alerts - runs on real patient ECG.

MIT-BIH has no SpO2, temperature or accelerometer channel: those are filled with normal
resting values. Ground truth (window contains an S/V beat) comes from the annotations.
"""

from __future__ import annotations

import pathlib

import numpy as np

from .generator import Window

DATA = pathlib.Path(__file__).resolve().parents[1] / "data" / "mitbih"
FS = 125


def available() -> list[str]:
    return sorted(p.stem for p in DATA.glob("*.npz"))


def replay_stream(record: str, n_windows: int | None = None, seed: int | None = None, start_s: float = 0.0):
    d = np.load(DATA / f"{record}.npz")
    ecg, peaks, labels = d["ecg"].astype(np.float32), d["peaks"], d["labels"]
    rng = np.random.default_rng(seed)
    n = FS * 10
    emitted = 0
    pos = int(start_s * FS)
    while n_windows is None or emitted < n_windows:
        if pos + n > len(ecg):
            pos = 0                                  # loop the 30-minute recording
        m = (peaks >= pos) & (peaks < pos + n)
        p = peaks[m]
        rr = np.diff(p) / FS
        hr = 60.0 / rr if len(rr) else np.array([60.0])
        lab = "".join(sorted(set(labels[m].tolist())))
        yield Window(
            ecg=ecg[pos:pos + n].copy(),
            hr_series=hr.astype(np.float32),
            spo2=float(np.clip(rng.normal(97.8, 0.5), 94, 100)),
            temp_c=float(np.clip(rng.normal(36.7, 0.2), 35, 38)),
            activity="rest",
            profile=f"mitbih-{record}" + (f"[{lab}]" if lab != "N" else ""),
            anomalous=bool(set(lab) - {"N"}),
        )
        emitted += 1
        pos += n
