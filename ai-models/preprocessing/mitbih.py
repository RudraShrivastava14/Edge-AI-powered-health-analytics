"""MIT-BIH Arrhythmia Database preprocessing.

Source: https://physionet.org/content/mitdb/1.0.0/ (Moody & Mark 2001; Goldberger et al. 2000)
License: Open Data Commons Attribution License v1.0.

Every record is converted to the project's common format: MLII lead, Butterworth band-pass
0.5-40 Hz (zero phase), resampled 360 -> 125 Hz. Beats are labelled with the AAMI EC57
classes used throughout the arrhythmia literature:

    N  normal / bundle-branch block      (N, L, R, e, j)
    S  supraventricular ectopic          (A, a, J, S)
    V  ventricular ectopic               (V, E)
    F  fusion of ventricular and normal  (F)
    Q  paced / unclassifiable            (/, f, Q)   -> excluded

Paced records (102, 104, 107, 217) are excluded per AAMI. The inter-patient split of
de Chazal et al. (2004) is used: DS1 for training, DS2 for testing, so no patient is ever
seen in both — splitting by beat would leak patients and inflate every metric.
"""

from __future__ import annotations

import pathlib

import numpy as np
from scipy.signal import butter, filtfilt, resample_poly

FS = 125
# F (fusion, 0.8 % of beats) is merged into V: it is part-ventricular, and with so few examples
# a separate class is unlearnable inter-patient. Classes: N, S, V.
AAMI = {**{s: "N" for s in "NLRej"}, **{s: "S" for s in "aJSA"}, **{s: "V" for s in "VEF"}}
CLASSES = ["N", "S", "V"]
N_RR = 5

DS1 = [101, 106, 108, 109, 112, 114, 115, 116, 118, 119, 122, 124,
       201, 203, 205, 207, 208, 209, 215, 220, 223, 230]
DS2 = [100, 103, 105, 111, 113, 117, 121, 123, 200, 202, 210, 212,
       213, 214, 219, 221, 222, 228, 231, 232, 233, 234]

BEAT_BEFORE, BEAT_AFTER = 36, 60          # samples at 125 Hz: 0.29 s before R, 0.48 s after
BEAT_LEN = BEAT_BEFORE + BEAT_AFTER


def bandpass(x, fs):
    b, a = butter(3, [0.5 / (fs / 2), 40 / (fs / 2)], btype="band")
    return filtfilt(b, a, x)


def load_record(path: pathlib.Path | str):
    """Return (signal_125hz float32, r_peak_indices, aami_labels) for one record."""
    import wfdb

    path = str(path)
    rec = wfdb.rdrecord(path)
    ann = wfdb.rdann(path, "atr")
    lead = rec.sig_name.index("MLII") if "MLII" in rec.sig_name else 0
    x = bandpass(rec.p_signal[:, lead], rec.fs)
    x = resample_poly(x, 25, 72).astype(np.float32)          # 360 * 25/72 = 125
    scale = FS / rec.fs
    peaks, labels = [], []
    for s, sym in zip(ann.sample, ann.symbol):
        if sym in AAMI:
            peaks.append(int(round(s * scale)))
            labels.append(AAMI[sym])
    return x, np.array(peaks), np.array(labels)


def rr_features(peaks: np.ndarray) -> np.ndarray:
    """Per-beat timing features (seconds / ratios):

    pre-RR, post-RR, local median RR (9 beats), pre/local (prematurity), post/pre (compensatory pause).
    Premature ectopic beats are defined by their timing as much as their shape. A median is
    used so the premature beat itself does not drag the reference down. Works on a single
    10-second window, which is all the cloud stage ever sees.
    """
    rr = np.diff(peaks) / FS
    pre = np.concatenate([[rr[0]], rr])
    post = np.concatenate([rr, [rr[-1]]])
    n = len(pre)
    local = np.array([np.median(pre[max(0, i - 4):i + 5]) for i in range(n)])
    return np.stack([pre, post, local, pre / np.maximum(local, 1e-3), post / np.maximum(pre, 1e-3)],
                    axis=1).astype(np.float32)


def beat_segments(x: np.ndarray, peaks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cut a fixed window around each R-peak; returns (segments [n, BEAT_LEN], valid_mask)."""
    ok = (peaks - BEAT_BEFORE >= 0) & (peaks + BEAT_AFTER <= len(x))
    seg = np.stack([x[p - BEAT_BEFORE:p + BEAT_AFTER] for p in peaks[ok]]) if ok.any() else np.zeros((0, BEAT_LEN))
    # Per-beat standardisation removes gain differences between leads/devices.
    seg = (seg - seg.mean(1, keepdims=True)) / (seg.std(1, keepdims=True) + 1e-6)
    return seg.astype(np.float32), ok


def local_templates(seg: np.ndarray, half: int = 8) -> np.ndarray:
    """Median of the neighbouring beats (+-half) for every beat: the patient's own typical beat.

    Ectopic beats differ from their neighbours; a bundle-branch-block patient's wide but
    regular beats do not. Giving the classifier [beat, template] makes it patient-relative.
    A 10-second window holds ~10-20 beats, so the cloud can compute this per window.
    """
    n = len(seg)
    return np.stack([np.median(seg[max(0, i - half):i + half + 1], axis=0) for i in range(n)]).astype(np.float32)


def beat_inputs(seg: np.ndarray) -> np.ndarray:
    """[n, 2, BEAT_LEN]: channel 0 = beat, channel 1 = local template."""
    return np.stack([seg, local_templates(seg)], axis=1)


def record_beats(path):
    x, peaks, labels = load_record(path)
    rr = rr_features(peaks)
    seg, ok = beat_segments(x, peaks)
    y = np.array([CLASSES.index(l) for l in labels[ok]])
    return beat_inputs(seg), rr[ok], y


def record_windows(path, window_s: int = 10):
    """Non-overlapping 10 s windows with window-level vitals + label (1 = any S/V/F beat)."""
    x, peaks, labels = load_record(path)
    n = FS * window_s
    out = []
    for start in range(0, len(x) - n, n):
        m = (peaks >= start) & (peaks < start + n)
        if m.sum() < 4:
            continue
        p = peaks[m]
        rr_ms = np.diff(p) / FS * 1000
        hr = 60000 / rr_ms
        out.append({
            "ecg": x[start:start + n], "peaks": p - start,
            "hr_mean": float(hr.mean()), "hr_min": float(hr.min()), "hr_max": float(hr.max()),
            "sdnn": float(rr_ms.std()), "label": int(any(l != "N" for l in labels[m])),
            "classes": "".join(sorted(set(labels[m]))),
        })
    return out
