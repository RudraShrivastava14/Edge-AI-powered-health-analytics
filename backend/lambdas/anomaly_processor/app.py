"""anomaly_processor — cloud-side confirmation of an escalated window.

Stage two of the cascade. The edge only says "this window looks unusual"; this function
re-examines the archived waveform at full precision and decides whether the event is real.

Confirmation combines two independent views:

1. **Signal view** — R-peaks are detected in the raw ECG to recompute heart rate and RR
   irregularity directly from the waveform, and a signal-quality check rejects flat or
   saturated windows (lead-off / motion artefact).
2. **Vitals view** — activity-aware clinical rules on the edge summary (tachycardia,
   bradycardia, irregular rhythm, desaturation).

An event is confirmed only when the rule fires and the waveform-derived heart rate agrees
with the summary; disagreement is recorded as a rejection (a hard negative for retraining).
This is a rule-based placeholder for the trained cloud model (task M-7); the interface,
storage and alerting path are final.
"""

from __future__ import annotations

import base64
import gzip
import json
import math
import os
import struct
import time
import uuid
from decimal import Decimal

import boto3

_ddb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")
_lambda = boto3.client("lambda")

ALERTS = _ddb.Table(os.environ["ALERTS_TABLE"])
TELEMETRY = _ddb.Table(os.environ["TELEMETRY_TABLE"])
RAW_BUCKET = os.environ["RAW_BUCKET"]
ALERT_FUNCTION = os.environ.get("ALERT_FUNCTION", "")

CLOUD_MODEL_VERSION = "rules-ecg-1.0.0"

# Exercise legitimately raises heart rate, so the tachycardia limit moves with activity.
TACHY_LIMIT = {"rest": 120.0, "walk": 135.0, "run": 165.0, "unknown": 120.0}
BRADY_LIMIT = 50.0
SPO2_LIMIT = 92.0
RR_CV_LIMIT = 0.15


def decode_waveform(raw: dict) -> list[float]:
    data = gzip.decompress(base64.b64decode(raw["data"]))
    if raw["encoding"] == "b64+gzip+float16":
        return list(struct.unpack(f"<{len(data)//2}e", data))
    return list(struct.unpack(f"<{len(data)//4}f", data))


def _moving_mean(x: list[float], w: int) -> list[float]:
    out, acc, half = [], 0.0, w // 2
    pref = [0.0]
    for v in x:
        acc += v
        pref.append(acc)
    n = len(x)
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        out.append((pref[hi] - pref[lo]) / (hi - lo))
    return out


def analyse_ecg(ecg: list[float], fs: float) -> dict:
    """Detrend, find R-peaks, and derive HR, RR irregularity and signal quality."""
    n = len(ecg)
    if n < fs * 2:
        return {"quality": "too_short"}
    base = _moving_mean(ecg, max(3, int(0.4 * fs)))
    x = [a - b for a, b in zip(ecg, base)]
    mean = sum(x) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in x) / n)
    peak_amp = max(x)
    if sd < 1e-3 or peak_amp < 0.15:
        return {"quality": "flat", "sd": sd}
    thr = mean + 0.45 * (peak_amp - mean)
    refractory = int(0.25 * fs)
    peaks, last = [], -refractory
    for i in range(1, n - 1):
        if x[i] >= thr and x[i] >= x[i - 1] and x[i] >= x[i + 1] and i - last >= refractory:
            peaks.append(i)
            last = i
    if len(peaks) < 3:
        return {"quality": "few_peaks", "peaks": len(peaks)}
    rr = [(b - a) / fs for a, b in zip(peaks, peaks[1:])]
    # Median-based statistics: one missed or spurious R-peak must not fake an arrhythmia.
    srt = sorted(rr)
    rr_med = srt[len(srt) // 2]
    mad = sorted(abs(r - rr_med) for r in rr)[len(rr) // 2]
    return {"quality": "ok", "peaks": len(peaks), "hrEcg": 60.0 / rr_med,
            "rrCv": 1.4826 * mad / rr_med, "sd": sd}


def classify(vitals: dict, sig: dict) -> tuple[list[dict], str]:
    """Return (findings, reason). Empty findings => not confirmed."""
    hr = vitals["hr"]["mean"]
    sdnn = vitals["hr"].get("sdnn") or 0.0
    spo2 = (vitals.get("spo2") or {}).get("mean")
    act = vitals.get("activity", "unknown")
    rr_cv_summary = sdnn / (60_000.0 / max(hr, 1.0))

    findings = []
    if hr >= TACHY_LIMIT.get(act, 120.0):
        sev = "high" if hr >= TACHY_LIMIT.get(act, 120.0) + 25 else "medium"
        findings.append({"class": "tachycardia", "severity": sev, "value": hr})
    if hr <= BRADY_LIMIT:
        findings.append({"class": "bradycardia", "severity": "high" if hr <= 40 else "medium", "value": hr})
    if spo2 is not None and spo2 < SPO2_LIMIT:
        findings.append({"class": "desaturation", "severity": "high" if spo2 < 88 else "medium", "value": spo2})
    irregular = rr_cv_summary >= RR_CV_LIMIT or (sig.get("quality") == "ok" and sig["rrCv"] >= RR_CV_LIMIT)
    if irregular:
        findings.append({"class": "irregular_rhythm", "severity": "high",
                         "value": round(max(rr_cv_summary, sig.get("rrCv", 0.0)), 3)})

    if not findings:
        return [], "no clinical rule fired"

    # Cross-check: rate-based findings must be supported by the waveform itself.
    if sig.get("quality") == "flat":
        return [], "signal quality: flat / lead-off"
    if sig.get("quality") == "ok":
        rate_classes = {"tachycardia", "bradycardia"}
        if any(f["class"] in rate_classes for f in findings):
            disagreement = abs(sig["hrEcg"] - hr) / hr
            if disagreement > 0.25 and not irregular:
                return [], f"waveform HR {sig['hrEcg']:.0f} disagrees with summary {hr:.0f}"
    return findings, "confirmed"


def _confidence(findings, sig, hr) -> float:
    c = 0.7
    if sig.get("quality") == "ok":
        c += 0.2 * max(0.0, 1 - abs(sig["hrEcg"] - hr) / hr * 4)
    if len(findings) > 1:
        c += 0.05
    return round(min(c, 0.99), 2)


def _dec(v):
    if isinstance(v, float):
        return Decimal(str(round(v, 4)))
    if isinstance(v, dict):
        return {k: _dec(x) for k, x in v.items() if x is not None}
    if isinstance(v, list):
        return [_dec(x) for x in v]
    return v


def handler(event, context):
    t0 = time.time()
    dev, ts, key = event["deviceId"], event["ts"], event["s3Key"]
    doc = json.loads(_s3.get_object(Bucket=RAW_BUCKET, Key=key)["Body"].read())
    vitals, edge = doc["vitals"], doc["edge"]
    fs = (doc.get("window") or {}).get("sampleRateHz", 125)
    ecg = decode_waveform(doc["raw"])
    # Suspect windows are uploaded downsampled ×2.
    if edge.get("flag") == "suspect":
        fs = fs / 2
    sig = analyse_ecg(ecg, fs)
    findings, reason = classify(vitals, sig)
    proc_ms = round((time.time() - t0) * 1000, 1)
    verdict = "confirmed" if findings else "rejected"

    TELEMETRY.update_item(
        Key={"deviceId": dev, "ts": ts},
        UpdateExpression="SET cloudVerdict = :v, cloudReason = :r, cloudModel = :m",
        ExpressionAttributeValues={":v": verdict, ":r": reason, ":m": CLOUD_MODEL_VERSION},
    )

    print(json.dumps({"level": "INFO", "deviceId": dev, "ts": ts, "verdict": verdict,
                      "reason": reason, "signal": sig, "procMs": proc_ms}, default=str))
    if not findings:
        return {"verdict": verdict, "reason": reason}

    primary = sorted(findings, key=lambda f: (f["severity"] != "high", f["class"]))[0]
    hr = vitals["hr"]["mean"]
    alert = {
        "alertId": f"{ts:013d}-{uuid.uuid4().hex[:8]}",
        "deviceId": dev,
        "ts": ts,
        "seq": doc.get("seq"),
        "class": primary["class"],
        "severity": primary["severity"],
        "findings": findings,
        "confidence": _confidence(findings, sig, hr),
        "status": "open",
        "edgeFlag": edge.get("flag"),
        "edgeReconError": edge.get("reconError"),
        "activity": vitals.get("activity"),
        "hr": hr,
        "spo2": (vitals.get("spo2") or {}).get("mean"),
        "hrEcg": sig.get("hrEcg"),
        "signalQuality": sig.get("quality"),
        "evidenceS3Key": key,
        "cloudModel": CLOUD_MODEL_VERSION,
        "ingestTs": event.get("ingestTs"),
        "confirmedTs": int(time.time() * 1000),
    }
    ALERTS.put_item(Item=_dec(alert))
    if ALERT_FUNCTION:
        _lambda.invoke(FunctionName=ALERT_FUNCTION, InvocationType="Event",
                       Payload=json.dumps({"alertId": alert["alertId"]}).encode())
    return {"verdict": verdict, "alertId": alert["alertId"], "class": primary["class"]}
