"""Cloud ECG classifier: R-peak detection + per-beat CNN (model/cloud_beat_classifier.onnx).

Preprocessing mirrors ai-models/preprocessing/mitbih.py exactly (band-pass 0.5-40 Hz at
125 Hz, 96-sample beats with 36 before the R-peak, per-beat z-score, [beat, local template]
input, 5 RR features). Only numpy + onnxruntime are needed, so the Lambda stays small.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np

FS = 125
BEAT_BEFORE, BEAT_AFTER = 36, 60
MODEL_DIR = pathlib.Path(__file__).resolve().parent / "model"

# scipy.signal.butter(3, [0.5, 40], btype="band", fs=125) — precomputed so scipy is not needed.
_B = np.array([0.29123384217688464, 0.0, -0.8737015265306539, 0.0, 0.8737015265306539, 0.0, -0.29123384217688464])
_A = np.array([1.0, -2.1499356060658683, 1.049375116231434, -0.04618574225954786, 0.4687775738709281,
               -0.24371550012887955, -0.0782779492136363])

_session = None
_meta = None


def _model():
    global _session, _meta
    if _session is None:
        import onnxruntime as ort

        _meta = json.loads((MODEL_DIR / "cloud_beat_classifier.json").read_text())
        _session = ort.InferenceSession(str(MODEL_DIR / "cloud_beat_classifier.onnx"), providers=["CPUExecutionProvider"])
    return _session, _meta


def _lfilter(b, a, x):
    y = np.zeros_like(x)
    nb, na = len(b), len(a)
    for n in range(len(x)):
        acc = 0.0
        for k in range(nb):
            if n - k >= 0:
                acc += b[k] * x[n - k]
        for k in range(1, na):
            if n - k >= 0:
                acc -= a[k] * y[n - k]
        y[n] = acc
    return y


def bandpass(x: np.ndarray) -> np.ndarray:
    """Zero-phase band-pass with odd-extension padding (filtfilt equivalent)."""
    x = np.asarray(x, dtype=np.float64)
    pad = min(250, len(x) - 1)
    ext = np.concatenate([2 * x[0] - x[pad:0:-1], x, 2 * x[-1] - x[-2:-pad - 2:-1]])
    y = _lfilter(_B, _A, ext)
    y = _lfilter(_B, _A, y[::-1])[::-1]
    return y[pad:-pad]


def resample_to_125(x: np.ndarray, fs: float) -> np.ndarray:
    if abs(fs - FS) < 1e-6:
        return np.asarray(x, dtype=np.float64)
    t_old = np.arange(len(x)) / fs
    t_new = np.arange(0, t_old[-1], 1 / FS)
    return np.interp(t_new, t_old, x)


def detect_r_peaks(x: np.ndarray) -> np.ndarray:
    """QRS detection: squared slope -> 150 ms moving integration -> adaptive threshold,
    then each detection is snapped to the largest |amplitude| within +-100 ms."""
    d = np.diff(x, prepend=x[0]) ** 2
    w = int(0.15 * FS)
    e = np.convolve(d, np.ones(w) / w, mode="same")
    thr = 0.3 * np.percentile(e, 99)
    refractory = int(0.25 * FS)
    peaks, last = [], -refractory
    for i in range(1, len(e) - 1):
        if e[i] >= thr and e[i] >= e[i - 1] and e[i] >= e[i + 1] and i - last >= refractory:
            lo, hi = max(0, i - int(0.1 * FS)), min(len(x), i + int(0.1 * FS))
            r = lo + int(np.argmax(np.abs(x[lo:hi])))
            if not peaks or r - peaks[-1] >= refractory:
                peaks.append(r)
                last = i
    return np.array(peaks, dtype=int)


def rr_features(peaks: np.ndarray) -> np.ndarray:
    rr = np.diff(peaks) / FS
    pre = np.concatenate([[rr[0]], rr])
    post = np.concatenate([rr, [rr[-1]]])
    local = np.array([np.median(pre[max(0, i - 4):i + 5]) for i in range(len(pre))])
    return np.stack([pre, post, local, pre / np.maximum(local, 1e-3), post / np.maximum(pre, 1e-3)], axis=1).astype(np.float32)


def beat_inputs(x: np.ndarray, peaks: np.ndarray):
    ok = (peaks - BEAT_BEFORE >= 0) & (peaks + BEAT_AFTER <= len(x))
    seg = np.stack([x[p - BEAT_BEFORE:p + BEAT_AFTER] for p in peaks[ok]]).astype(np.float32)
    seg = (seg - seg.mean(1, keepdims=True)) / (seg.std(1, keepdims=True) + 1e-6)
    tmpl = np.stack([np.median(seg[max(0, i - 8):i + 9], axis=0) for i in range(len(seg))]).astype(np.float32)
    return np.stack([seg, tmpl], axis=1), ok


def classify_window(ecg, fs: float) -> dict:
    """Classify every beat in a window. Returns a JSON-safe summary."""
    session, meta = _model()
    x = bandpass(resample_to_125(np.asarray(ecg, dtype=np.float64), fs))
    if np.std(x) < 1e-3:
        return {"quality": "flat", "beats": 0}
    peaks = detect_r_peaks(x)
    if len(peaks) < 3:
        return {"quality": "few_beats", "beats": int(len(peaks))}
    rr = rr_features(peaks)
    beats, ok = beat_inputs(x, peaks)
    if ok.sum() < 3:
        return {"quality": "few_beats", "beats": int(ok.sum())}
    probs = session.run(None, {"beat": beats, "rr": rr[ok]})[0]
    p_abn = probs[:, 1:].sum(1)
    thr = meta["window_decision"]["beat_prob_threshold"]
    abnormal = p_abn >= thr
    cls = probs.argmax(1)
    counts = {c: int((cls == i).sum()) for i, c in enumerate(meta["classes"])}
    abn_counts = {c: int(((cls == i) & abnormal).sum()) for i, c in enumerate(meta["classes"]) if c != "N"}
    rr_s = np.diff(peaks) / FS
    med = float(np.median(rr_s))
    return {
        "quality": "ok", "model": meta["version"], "beats": int(len(probs)),
        "beatCounts": counts, "abnormalBeats": abn_counts, "nAbnormal": int(abnormal.sum()),
        "maxAbnormalProb": round(float(p_abn.max()), 4),
        "abnormal": bool(abnormal.sum() >= meta["window_decision"]["min_abnormal_beats"]),
        "hrEcg": round(60.0 / med, 1),
        "rrCv": round(float(1.4826 * np.median(np.abs(rr_s - med)) / med), 4),
    }
