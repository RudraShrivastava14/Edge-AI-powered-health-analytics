"""Uplink policy — the core of the edge/cloud split.

Decides, per window, how much data is worth sending. This single decision is what keeps the
project inside the AWS IoT Core free-tier message quota and is the source of the bandwidth
result reported in ``results/benchmarks/bandwidth.md``.

Placeholder scoring is used until the trained TFLite autoencoder lands (task M-6b): the
interface is stable, only ``score_window`` changes.
"""

from __future__ import annotations

import base64
import gzip
import json
import zlib
from dataclasses import dataclass
from enum import Enum

import numpy as np


class Flag(str, Enum):
    NORMAL = "normal"
    SUSPECT = "suspect"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Thresholds:
    """Reconstruction-error thresholds.

    Chosen on the validation set at a fixed false-negative budget (see RQ1), then frozen.
    Overridable per device at runtime via the ``hh/v1/{deviceId}/config`` topic, so the
    operating point can be tuned without reflashing the device.
    """

    tau_low: float = 0.030
    tau_high: float = 0.075

    #: Activity multiplies the thresholds: motion artefacts inflate reconstruction error,
    #: so we tolerate more of it while the wearer is moving (research question RQ5).
    activity_scale: dict = None

    def scaled(self, activity: str) -> tuple[float, float]:
        scale = (self.activity_scale or {"rest": 1.0, "walk": 1.4, "run": 2.0}).get(activity, 1.0)
        return self.tau_low * scale, self.tau_high * scale

    def __post_init__(self):
        if self.tau_low >= self.tau_high:
            raise ValueError("tau_low must be strictly less than tau_high")


def classify(recon_error: float, activity: str, thresholds: Thresholds) -> Flag:
    """Map a reconstruction error to an uplink flag."""
    low, high = thresholds.scaled(activity)
    if recon_error >= high:
        return Flag.CRITICAL
    if recon_error >= low:
        return Flag.SUSPECT
    return Flag.NORMAL


def encode_window(ecg: np.ndarray, downsample: int = 1) -> str:
    """Encode an ECG window for transport: float16 -> gzip -> base64.

    float16 is plenty for a signal we normalised anyway, and halves the payload versus
    float32. ``downsample=2`` is used for ``suspect`` windows, which need to be reviewable
    but not diagnostic-grade.
    """
    arr = np.asarray(ecg, dtype=np.float32)[::downsample].astype(np.float16)
    return base64.b64encode(gzip.compress(arr.tobytes(), compresslevel=6)).decode("ascii")


def build_payload(
    device_id: str,
    ts_ms: int,
    seq: int,
    window,                       # simulator.generator.Window (duck-typed)
    recon_error: float,
    flag: Flag,
    model_version: str = "ae-int8-0.0.0-stub",
    inference_ms: float = 0.0,
    battery: float = 1.0,
    fw_version: str = "0.1.0",
    buffered_replay: bool = False,
) -> dict:
    """Build a ``hh.telemetry.v1`` payload (see docs/architecture/API_CONTRACT.md)."""
    hr = window.hr_stats
    payload = {
        "schema": "hh.telemetry.v1",
        "deviceId": device_id,
        "ts": ts_ms,
        "seq": seq,
        "window": {"durationMs": 10_000, "sampleRateHz": 125},
        "vitals": {
            "hr": {k: round(v, 2) for k, v in hr.items()},
            "spo2": {"mean": round(window.spo2, 1), "min": round(window.spo2 - 0.5, 1)},
            "tempC": {"mean": round(window.temp_c, 2)},
            "activity": window.activity,
        },
        "edge": {
            "modelVersion": model_version,
            "reconError": round(float(recon_error), 5),
            "flag": flag.value,
            "inferenceMs": round(float(inference_ms), 1),
        },
        "meta": {
            "battery": round(battery, 2),
            "fwVersion": fw_version,
            "bufferedReplay": buffered_replay,
        },
    }

    if flag is not Flag.NORMAL:
        payload["raw"] = {
            "encoding": "b64+gzip+float16",
            "channels": ["ecg"],
            "s3Hint": None,
            "data": encode_window(window.ecg, downsample=2 if flag is Flag.SUSPECT else 1),
        }
    return payload


def score_window(window) -> tuple[float, float]:
    """Return ``(reconstruction_error, inference_ms)``.

    STUB (task M-6b): until the TFLite autoencoder is trained, we approximate "how unusual
    is this window" with cheap signal statistics that correlate with the real thing — how
    far the heart rate sits outside the normal band, RR-interval variability, and hypoxia.
    Replace the body with a TFLite interpreter call; the signature stays the same.

    The constants are calibrated so that the default :class:`Thresholds` separate the
    simulator's healthy and abnormal profiles. They carry no clinical meaning and are
    discarded once the trained model lands.
    """
    import time

    t0 = time.perf_counter()
    hr = window.hr_stats
    mean_hr = hr["mean"]

    # Distance outside the normal resting band [55, 100] bpm, asymmetric: bradycardia is
    # a smaller absolute deviation than tachycardia but no less significant.
    hr_dev = max(0.0, mean_hr - 100.0) / 40.0 + max(0.0, 55.0 - mean_hr) / 12.0

    # Coefficient of variation of RR intervals — scale-free, so it flags irregularity
    # rather than simply a fast or slow rate.
    mean_rr_ms = 60_000.0 / max(mean_hr, 1.0)
    rr_cv = hr["sdnn"] / mean_rr_ms

    hypoxia = max(0.0, (95.0 - window.spo2) / 25.0)

    error = float(0.006 + 0.09 * hr_dev + 0.25 * rr_cv + 0.35 * hypoxia)
    return error, (time.perf_counter() - t0) * 1000.0


def payload_bytes(payload: dict) -> int:
    """Serialised size — used by the bandwidth benchmark (E5)."""
    return len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def baseline_bytes(window, sample_rate_hz: int = 125, seconds: int = 10) -> int:
    """Bytes a naive 'stream every raw sample' client would send for the same window.

    This is the denominator of the headline bandwidth-reduction figure, so compute it
    honestly: assume the baseline also compresses, otherwise the comparison is rigged.
    """
    raw = np.asarray(window.ecg, dtype=np.float32).tobytes()
    return len(zlib.compress(raw, 6))
