"""Synthetic vital-sign generator.

Produces physiologically plausible 10-second windows so the whole pipeline can be
developed and demonstrated without any wearable hardware. Deliberately dependency-light
(NumPy only) so it runs on a Raspberry Pi or in CI.

Not a physiological model — it is good enough to exercise the pipeline and to make the
demo legible, and that is all it claims to be.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

SAMPLE_RATE_HZ = 125
WINDOW_SECONDS = 10
WINDOW_SAMPLES = SAMPLE_RATE_HZ * WINDOW_SECONDS

#: profile -> (hr_mean, hr_sd, spo2_mean, spo2_sd, rr_irregularity, label)
PROFILES: dict[str, dict] = {
    "healthy": dict(hr=75.0, hr_sd=4.0, spo2=98.0, spo2_sd=0.6, irregularity=0.02, anomalous=False),
    "tachycardia": dict(hr=135.0, hr_sd=6.0, spo2=96.5, spo2_sd=0.8, irregularity=0.03, anomalous=True),
    "bradycardia": dict(hr=44.0, hr_sd=3.0, spo2=96.0, spo2_sd=0.8, irregularity=0.03, anomalous=True),
    "arrhythmia": dict(hr=88.0, hr_sd=5.0, spo2=97.0, spo2_sd=0.7, irregularity=0.35, anomalous=True),
    "hypoxia": dict(hr=98.0, hr_sd=5.0, spo2=87.0, spo2_sd=1.5, irregularity=0.05, anomalous=True),
}

#: `mixed` alternates between healthy stretches and injected episodes.
EPISODE_PROFILES = ("tachycardia", "bradycardia", "arrhythmia", "hypoxia")


@dataclass
class Window:
    """One 10-second observation window."""

    ecg: np.ndarray                 # shape (WINDOW_SAMPLES,), float32, normalised
    hr_series: np.ndarray           # instantaneous HR per beat, bpm
    spo2: float
    temp_c: float
    activity: str
    profile: str
    anomalous: bool                 # ground truth, used for offline evaluation only
    accel: np.ndarray = field(repr=False, default=None)  # shape (WINDOW_SAMPLES, 3)

    @property
    def hr_stats(self) -> dict[str, float]:
        hr = self.hr_series
        rr_ms = 60_000.0 / np.clip(hr, 20, 240)
        return {
            "mean": float(np.mean(hr)),
            "min": float(np.min(hr)),
            "max": float(np.max(hr)),
            # SDNN: standard deviation of RR intervals, the standard HRV time-domain metric
            "sdnn": float(np.std(rr_ms)) if rr_ms.size > 1 else 0.0,
        }


def _ecg_beat(length: int, amplitude: float, rng: np.random.Generator) -> np.ndarray:
    """A crude PQRST complex: sum of Gaussians at the usual relative offsets."""
    t = np.linspace(0.0, 1.0, length, endpoint=False)
    # (centre, height, width) for P, Q, R, S, T
    components = (
        (0.18, 0.10, 0.025),
        (0.33, -0.12, 0.012),
        (0.37, 1.00, 0.010),
        (0.42, -0.25, 0.014),
        (0.62, 0.28, 0.045),
    )
    beat = np.zeros_like(t)
    for centre, height, width in components:
        beat += height * np.exp(-0.5 * ((t - centre) / width) ** 2)
    return (beat * amplitude).astype(np.float32)


def _activity_for(profile: str, rng: np.random.Generator) -> str:
    """Activity context. Exercise legitimately raises HR — the detector must know."""
    return str(rng.choice(["rest", "walk", "run"], p=[0.7, 0.22, 0.08]))


def generate_window(
    profile: str = "healthy",
    rng: np.random.Generator | None = None,
    noise_sd: float = 0.02,
) -> Window:
    """Generate a single window for the named profile."""
    rng = rng or np.random.default_rng()
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; choose from {sorted(PROFILES)}")

    cfg = PROFILES[profile]
    activity = _activity_for(profile, rng)
    # Exertion raises heart rate; the model sees this via the activity feature.
    hr_offset = {"rest": 0.0, "walk": 12.0, "run": 35.0}[activity]

    ecg = np.zeros(WINDOW_SAMPLES, dtype=np.float32)
    hr_series: list[float] = []
    cursor = 0
    while cursor < WINDOW_SAMPLES:
        hr = float(rng.normal(cfg["hr"] + hr_offset, cfg["hr_sd"]))
        # RR irregularity is what makes an arrhythmia look like an arrhythmia.
        hr *= 1.0 + rng.normal(0.0, cfg["irregularity"])
        hr = float(np.clip(hr, 25.0, 220.0))
        hr_series.append(hr)

        beat_len = max(8, int(SAMPLE_RATE_HZ * 60.0 / hr))
        beat = _ecg_beat(beat_len, amplitude=float(rng.normal(1.0, 0.05)), rng=rng)
        end = min(cursor + beat_len, WINDOW_SAMPLES)
        ecg[cursor:end] += beat[: end - cursor]
        cursor = end

    # Baseline wander (respiration) + sensor noise; motion adds a lot more of both.
    t = np.arange(WINDOW_SAMPLES) / SAMPLE_RATE_HZ
    motion_gain = {"rest": 1.0, "walk": 2.5, "run": 5.0}[activity]
    ecg += 0.08 * motion_gain * np.sin(2 * math.pi * 0.25 * t).astype(np.float32)
    ecg += rng.normal(0.0, noise_sd * motion_gain, WINDOW_SAMPLES).astype(np.float32)

    accel_sd = {"rest": 0.02, "walk": 0.25, "run": 0.9}[activity]
    accel = rng.normal(0.0, accel_sd, (WINDOW_SAMPLES, 3)).astype(np.float32)
    accel[:, 2] += 1.0  # gravity on Z

    return Window(
        ecg=ecg,
        hr_series=np.asarray(hr_series, dtype=np.float32),
        spo2=float(np.clip(rng.normal(cfg["spo2"], cfg["spo2_sd"]), 70.0, 100.0)),
        temp_c=float(np.clip(rng.normal(36.7, 0.25), 34.0, 41.0)),
        activity=activity,
        profile=profile,
        anomalous=bool(cfg["anomalous"]),
        accel=accel,
    )


def generate_stream(
    profile: str = "mixed",
    n_windows: int | None = None,
    seed: int | None = None,
    episode_len: int = 4,
    episode_prob: float = 0.02,
):
    """Yield windows indefinitely (or `n_windows` of them).

    The ``mixed`` profile spends most of its time healthy and occasionally drops into a
    multi-window abnormal episode — this is the realistic demo profile, and the one the
    bandwidth benchmark should use.
    """
    rng = np.random.default_rng(seed)
    emitted = 0
    episode_remaining = 0
    episode_profile = "healthy"

    while n_windows is None or emitted < n_windows:
        if profile == "mixed":
            if episode_remaining > 0:
                current = episode_profile
                episode_remaining -= 1
            elif rng.random() < episode_prob:
                episode_profile = str(rng.choice(EPISODE_PROFILES))
                episode_remaining = episode_len - 1
                current = episode_profile
            else:
                current = "healthy"
        else:
            current = profile

        yield generate_window(current, rng=rng)
        emitted += 1
