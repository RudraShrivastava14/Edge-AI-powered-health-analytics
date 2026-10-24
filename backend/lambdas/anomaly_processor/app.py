"""anomaly_processor — cloud-side confirmation of an escalated window.

Stage two of the cascade. The tiny edge model only says "this window looks unusual"; this
function re-examines the archived full waveform and decides whether the event is real.

Decision = strong ML model + clinical vital-sign rules:

1. **ML (beat classifier)** — model/cloud_beat_classifier.onnx, a 1-D CNN trained on the
   MIT-BIH Arrhythmia Database (inter-patient). Every beat in the window is classified as
   N / S (supraventricular ectopic) / V (ventricular ectopic). The window is ML-abnormal if
   any beat has P(S)+P(V) >= 0.9.
2. **Vital-sign rules** for conditions that are about rate or oxygen rather than beat shape:
   tachycardia / bradycardia (from the heart rate measured on the waveform itself,
   activity-aware) and desaturation (SpO2).

Confirmed -> Alert + alert_dispatcher. Rejected -> recorded on the telemetry item as a hard
negative for the next retraining round.
"""

from __future__ import annotations

import base64
import gzip
import json
import os
import time
import uuid
from decimal import Decimal

import boto3
import numpy as np

import ecg_ml

_ddb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")
_lambda = boto3.client("lambda")

ALERTS = _ddb.Table(os.environ["ALERTS_TABLE"])
TELEMETRY = _ddb.Table(os.environ["TELEMETRY_TABLE"])
RAW_BUCKET = os.environ["RAW_BUCKET"]
ALERT_FUNCTION = os.environ.get("ALERT_FUNCTION", "")

# Exercise legitimately raises heart rate, so the tachycardia limit moves with activity.
TACHY_LIMIT = {"rest": 120.0, "walk": 135.0, "run": 165.0, "unknown": 120.0}
BRADY_LIMIT = 50.0
SPO2_LIMIT = 92.0


def decode_waveform(raw: dict) -> np.ndarray:
    data = gzip.decompress(base64.b64decode(raw["data"]))
    dtype = np.float16 if raw["encoding"] == "b64+gzip+float16" else np.float32
    return np.frombuffer(data, dtype="<" + np.dtype(dtype).str[1:]).astype(np.float64)


def decide(vitals: dict, ml: dict) -> tuple[list[dict], str]:
    """Return (findings, reason). Empty findings => rejected."""
    if ml.get("quality") == "flat":
        return [], "signal quality: flat / lead-off"
    act = vitals.get("activity", "unknown")
    hr = ml.get("hrEcg") or vitals["hr"]["mean"]          # prefer the rate measured on the waveform
    spo2 = (vitals.get("spo2") or {}).get("mean")
    findings = []

    if ml.get("abnormal"):
        ab = ml["abnormalBeats"]
        if ab.get("V", 0) >= ab.get("S", 0):
            findings.append({"class": "ventricular_ectopy", "severity": "high" if ab.get("V", 0) >= 3 else "medium",
                             "value": ab.get("V", 0), "source": "ml"})
        else:
            findings.append({"class": "supraventricular_ectopy", "severity": "medium", "value": ab.get("S", 0),
                             "source": "ml"})
    limit = TACHY_LIMIT.get(act, 120.0)
    if hr >= limit:
        findings.append({"class": "tachycardia", "severity": "high" if hr >= limit + 25 else "medium",
                         "value": round(hr, 1), "source": "rule"})
    if hr <= BRADY_LIMIT:
        findings.append({"class": "bradycardia", "severity": "high" if hr <= 40 else "medium",
                         "value": round(hr, 1), "source": "rule"})
    if spo2 is not None and spo2 < SPO2_LIMIT:
        findings.append({"class": "desaturation", "severity": "high" if spo2 < 88 else "medium",
                         "value": spo2, "source": "rule"})

    if not findings:
        return [], (f"ML: {ml.get('beats', 0)} beats all normal (max P(abnormal) {ml.get('maxAbnormalProb', 0)}); "
                    f"HR {hr:.0f} and SpO2 within limits")
    return findings, "confirmed"


def _confidence(findings, ml) -> float:
    ml_f = [f for f in findings if f["source"] == "ml"]
    if ml_f:
        c = float(ml.get("maxAbnormalProb", 0.9))
    else:
        c = 0.85 if ml.get("quality") == "ok" else 0.7
    if len(findings) > 1:
        c += 0.03
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
    if edge.get("flag") == "suspect":      # suspect windows are uploaded downsampled x2
        fs = fs / 2
    ecg = decode_waveform(doc["raw"])
    ml = ecg_ml.classify_window(ecg, fs)
    findings, reason = decide(vitals, ml)
    proc_ms = round((time.time() - t0) * 1000, 1)
    verdict = "confirmed" if findings else "rejected"
    model_version = ml.get("model", "beatcnn")

    TELEMETRY.update_item(
        Key={"deviceId": dev, "ts": ts},
        UpdateExpression="SET cloudVerdict = :v, cloudReason = :r, cloudModel = :m, cloudMl = :ml",
        ExpressionAttributeValues=_dec({":v": verdict, ":r": reason, ":m": model_version, ":ml": ml}),
    )
    print(json.dumps({"level": "INFO", "deviceId": dev, "ts": ts, "verdict": verdict, "reason": reason,
                      "ml": ml, "procMs": proc_ms}, default=str))
    if not findings:
        return {"verdict": verdict, "reason": reason, "ml": ml}

    primary = sorted(findings, key=lambda f: (f["severity"] != "high", f["source"] != "ml", f["class"]))[0]
    alert = {
        "alertId": f"{ts:013d}-{uuid.uuid4().hex[:8]}",
        "deviceId": dev,
        "ts": ts,
        "seq": doc.get("seq"),
        "class": primary["class"],
        "severity": primary["severity"],
        "findings": findings,
        "confidence": _confidence(findings, ml),
        "status": "open",
        "edgeFlag": edge.get("flag"),
        "edgeReconError": edge.get("reconError"),
        "edgeModel": edge.get("modelVersion"),
        "activity": vitals.get("activity"),
        "hr": vitals["hr"]["mean"],
        "spo2": (vitals.get("spo2") or {}).get("mean"),
        "hrEcg": ml.get("hrEcg"),
        "beats": ml.get("beats"),
        "beatCounts": ml.get("beatCounts"),
        "abnormalBeats": ml.get("abnormalBeats"),
        "signalQuality": ml.get("quality"),
        "evidenceS3Key": key,
        "cloudModel": model_version,
        "cloudMs": proc_ms,
        "ingestTs": event.get("ingestTs"),
        "confirmedTs": int(time.time() * 1000),
    }
    ALERTS.put_item(Item=_dec(alert))
    if ALERT_FUNCTION:
        _lambda.invoke(FunctionName=ALERT_FUNCTION, InvocationType="Event",
                       Payload=json.dumps({"alertId": alert["alertId"]}).encode())
    return {"verdict": verdict, "alertId": alert["alertId"], "class": primary["class"], "ml": ml}
