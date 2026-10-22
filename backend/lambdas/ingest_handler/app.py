"""ingest_handler — entry point for every telemetry message.

Triggered by the IoT Rule ``SELECT *, topic(3) AS topicDeviceId FROM 'hh/v1/+/telemetry'``.

Validates the hh.telemetry.v1 payload, writes the compact summary to DynamoDB, and for
suspect/critical windows archives the waveform to S3 and asynchronously hands the event to
anomaly_processor for cloud-side confirmation. Malformed payloads are quarantined in S3,
never silently dropped.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from decimal import Decimal

import boto3

_ddb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")
_lambda = boto3.client("lambda")

TELEMETRY = _ddb.Table(os.environ["TELEMETRY_TABLE"])
DEVICES = _ddb.Table(os.environ["DEVICES_TABLE"])
RAW_BUCKET = os.environ["RAW_BUCKET"]
ANOMALY_FUNCTION = os.environ.get("ANOMALY_FUNCTION", "")
TTL_DAYS = int(os.environ.get("TELEMETRY_TTL_DAYS", "30"))

DEVICE_RE = re.compile(r"^[A-Za-z0-9._-]{3,64}$")
FLAGS = {"normal", "suspect", "critical"}
ACTIVITIES = {"rest", "walk", "run", "unknown"}


class ValidationError(ValueError):
    pass


def validate(p: dict, topic_device: str | None) -> None:
    """Enforce the parts of telemetry.v1 that downstream code relies on."""
    if p.get("schema") != "hh.telemetry.v1":
        raise ValidationError("schema must be hh.telemetry.v1")
    dev = p.get("deviceId")
    if not isinstance(dev, str) or not DEVICE_RE.match(dev):
        raise ValidationError("invalid deviceId")
    if topic_device and topic_device != dev:
        raise ValidationError("deviceId does not match topic")
    if not isinstance(p.get("ts"), int) or p["ts"] < 1_600_000_000_000:
        raise ValidationError("ts must be epoch milliseconds")
    if not isinstance(p.get("seq"), int) or p["seq"] < 0:
        raise ValidationError("seq must be a non-negative integer")
    hr = (p.get("vitals") or {}).get("hr") or {}
    if not isinstance(hr.get("mean"), (int, float)) or not 20 <= hr["mean"] <= 250:
        raise ValidationError("vitals.hr.mean out of range")
    edge = p.get("edge") or {}
    if edge.get("flag") not in FLAGS:
        raise ValidationError("edge.flag invalid")
    if not isinstance(edge.get("reconError"), (int, float)):
        raise ValidationError("edge.reconError missing")
    if edge["flag"] == "normal" and "raw" in p:
        raise ValidationError("normal windows must not carry raw data")
    if edge["flag"] != "normal":
        raw = p.get("raw") or {}
        if not raw.get("data") or raw.get("encoding") not in ("b64+gzip+float16", "b64+gzip+float32"):
            raise ValidationError("escalated window missing raw waveform")


def _dec(v):
    """DynamoDB wants Decimal, not float."""
    if isinstance(v, float):
        return Decimal(str(round(v, 5)))
    if isinstance(v, dict):
        return {k: _dec(x) for k, x in v.items() if x is not None}
    if isinstance(v, list):
        return [_dec(x) for x in v]
    return v


def _quarantine(event: dict, reason: str) -> None:
    key = f"quarantine/{datetime.now(timezone.utc):%Y/%m/%d}/{int(time.time()*1000)}.json"
    _s3.put_object(Bucket=RAW_BUCKET, Key=key,
                   Body=json.dumps({"reason": reason, "payload": event}, default=str).encode())
    print(json.dumps({"level": "WARN", "msg": "quarantined", "reason": reason, "key": key}))


def handler(event, context):
    ingest_ts = int(time.time() * 1000)
    topic_device = event.pop("topicDeviceId", None)
    payload_bytes = len(json.dumps(event, separators=(",", ":")).encode())
    try:
        validate(event, topic_device)
    except ValidationError as exc:
        _quarantine(event, str(exc))
        return {"status": "quarantined", "reason": str(exc)}

    dev, ts, seq = event["deviceId"], event["ts"], event["seq"]
    vit, edge = event["vitals"], event["edge"]
    hr = vit["hr"]
    flag = edge["flag"]

    item = {
        "deviceId": dev,
        "ts": ts,
        "seq": seq,
        "hr": hr.get("mean"),
        "hrMin": hr.get("min"),
        "hrMax": hr.get("max"),
        "sdnn": hr.get("sdnn"),
        "spo2": (vit.get("spo2") or {}).get("mean"),
        "tempC": (vit.get("tempC") or {}).get("mean"),
        "activity": vit.get("activity") if vit.get("activity") in ACTIVITIES else "unknown",
        "flag": flag,
        "reconError": edge.get("reconError"),
        "modelVersion": edge.get("modelVersion"),
        "payloadBytes": payload_bytes,
        "ingestTs": ingest_ts,
        "edgeToIngestMs": ingest_ts - ts,
        "bufferedReplay": bool((event.get("meta") or {}).get("bufferedReplay", False)),
        "expiresAt": ingest_ts // 1000 + TTL_DAYS * 86400,
    }

    s3_key = None
    if flag != "normal":
        d = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        s3_key = f"raw-windows/{d:%Y/%m/%d}/{dev}/{ts}-{seq}.json"
        _s3.put_object(
            Bucket=RAW_BUCKET, Key=s3_key, ContentType="application/json",
            Body=json.dumps({"deviceId": dev, "ts": ts, "seq": seq, "raw": event["raw"],
                             "vitals": vit, "edge": edge, "window": event.get("window")}).encode(),
        )
        item["s3Key"] = s3_key
        item["cloudVerdict"] = "pending"

    TELEMETRY.put_item(Item=_dec(item))

    meta = event.get("meta") or {}
    DEVICES.update_item(
        Key={"deviceId": dev},
        UpdateExpression="SET lastSeen = :t, lastFlag = :f, battery = :b, fwVersion = :fw, "
                         "#s = :on, lastHr = :hr, lastSpo2 = :sp, "
                         "label = if_not_exists(label, :dev), createdAt = if_not_exists(createdAt, :t)",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues=_dec({
            ":t": ts, ":f": flag, ":b": float(meta.get("battery", 1.0)),
            ":fw": str(meta.get("fwVersion", "unknown")), ":on": "online",
            ":hr": float(hr["mean"]), ":sp": float(item["spo2"] or 0), ":dev": dev,
        }),
    )

    if s3_key and ANOMALY_FUNCTION:
        _lambda.invoke(
            FunctionName=ANOMALY_FUNCTION, InvocationType="Event",
            Payload=json.dumps({"deviceId": dev, "ts": ts, "seq": seq, "s3Key": s3_key,
                                "ingestTs": ingest_ts}).encode(),
        )

    print(json.dumps({"level": "INFO", "deviceId": dev, "seq": seq, "flag": flag,
                      "bytes": payload_bytes, "edgeToIngestMs": ingest_ts - ts}))
    return {"status": "ok", "flag": flag, "s3Key": s3_key}
