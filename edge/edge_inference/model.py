"""ONNX edge model: 1-D convolutional autoencoder anomaly scorer.

Loads ai-models/models/ecg_autoencoder.onnx (trained by ai-models/training/train_autoencoder.py)
and scores each 10-second ECG window by its reconstruction error. Thresholds come from the
model's metadata file and are per activity, because motion raises reconstruction error.

Low SpO2 is not visible in an ECG, so a separate, explicitly rule-based SpO2 guard escalates
desaturation independently of the model.
"""

from __future__ import annotations

import json
import pathlib
import time

import numpy as np

from .policy import Flag

DEFAULT_MODEL = pathlib.Path(__file__).resolve().parents[2] / "ai-models" / "models" / "ecg_autoencoder.onnx"

SPO2_SUSPECT = 93.0
SPO2_CRITICAL = 90.0


class OnnxScorer:
    def __init__(self, onnx_path: pathlib.Path | str = DEFAULT_MODEL):
        import onnxruntime as ort

        self.path = pathlib.Path(onnx_path)
        self.meta = json.loads(self.path.with_suffix(".json").read_text())
        self.thresholds = self.meta["thresholds_by_activity"]
        self.win = self.meta["input"]["shape"][-1]
        self.version = self.meta["version"]
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(str(self.path), opts, providers=["CPUExecutionProvider"])

    def preprocess(self, ecg) -> np.ndarray:
        x = np.asarray(ecg, dtype=np.float32)[: self.win]
        x = (x - x.mean()) / (x.std() + 1e-6)
        return x[None, None, :]

    def score(self, window) -> tuple[float, float]:
        """Return (reconstruction_error, inference_ms)."""
        t0 = time.perf_counter()
        x = self.preprocess(window.ecg)
        recon = self.session.run(None, {"ecg": x})[0]
        err = float(np.mean((recon - x) ** 2))
        return err, (time.perf_counter() - t0) * 1000.0

    def classify(self, error: float, window) -> Flag:
        thr = self.thresholds.get(window.activity, self.thresholds["rest"])
        if error >= thr["tau_high"] or window.spo2 < SPO2_CRITICAL:
            return Flag.CRITICAL
        if error >= thr["tau_low"] or window.spo2 < SPO2_SUSPECT:
            return Flag.SUSPECT
        return Flag.NORMAL


TINY_MODEL = pathlib.Path(__file__).resolve().parents[1] / "models" / "edge_tiny.onnx"


class TinyScorer:
    """The deployed edge model: a 33-parameter network over 6 vitals features (edge/models/edge_tiny.onnx).

    It lives on the gateway only and is never uploaded to AWS. Output is P(abnormal) for the
    window; thresholds come from edge_tiny.json (tau_low tuned for >= 95 % validation recall,
    because the strong cloud classifier removes the false alarms).
    """

    def __init__(self, onnx_path: pathlib.Path | str = TINY_MODEL):
        import onnxruntime as ort

        self.path = pathlib.Path(onnx_path)
        self.meta = json.loads(self.path.with_suffix(".json").read_text())
        self.tau_low = self.meta["thresholds"]["tau_low"]
        self.tau_high = self.meta["thresholds"]["tau_high"]
        self.version = self.meta["version"]
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(str(self.path), opts, providers=["CPUExecutionProvider"])

    @staticmethod
    def features(window) -> np.ndarray:
        h = window.hr_stats
        rr_mean = 60000.0 / max(h["mean"], 1.0)
        return np.array([[h["mean"], h["max"] - h["min"], h["sdnn"] / rr_mean, window.spo2,
                          float(window.activity == "walk"), float(window.activity == "run")]], dtype=np.float32)

    def score(self, window) -> tuple[float, float]:
        t0 = time.perf_counter()
        p = float(self.session.run(None, {"features": self.features(window)})[0][0, 0])
        return p, (time.perf_counter() - t0) * 1000.0

    def classify(self, p: float, window) -> Flag:
        if p >= self.tau_high or window.spo2 < SPO2_CRITICAL:
            return Flag.CRITICAL
        if p >= self.tau_low or window.spo2 < SPO2_SUSPECT:
            return Flag.SUSPECT
        return Flag.NORMAL
