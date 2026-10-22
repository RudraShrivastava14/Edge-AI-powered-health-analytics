"""api_handler — REST query layer behind API Gateway (HTTP API, Cognito JWT authorizer).

Routes (see docs/architecture/API_CONTRACT.md):
  GET  /v1/health
  GET  /v1/devices                         POST /v1/devices
  GET  /v1/devices/{deviceId}/vitals       ?from&to&limit&cursor
  GET  /v1/devices/{deviceId}/vitals/latest
  GET  /v1/devices/{deviceId}/stats        ?hours=24
  GET  /v1/alerts                          ?status=open|acknowledged|all&deviceId&limit&cursor
  POST /v1/alerts/{alertId}/ack
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

_ddb = boto3.resource("dynamodb")
TELEMETRY = _ddb.Table(os.environ["TELEMETRY_TABLE"])
ALERTS = _ddb.Table(os.environ["ALERTS_TABLE"])
DEVICES = _ddb.Table(os.environ["DEVICES_TABLE"])
VERSION = "1.0.0"
DEVICE_RE = re.compile(r"^[A-Za-z0-9._-]{3,64}$")
ONLINE_WINDOW_MS = 60_000


class _Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o == o.to_integral_value() else float(o)
        return super().default(o)


def _resp(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json"},
            "body": json.dumps(body, cls=_Enc)}


def _problem(status, title, detail, ctx):
    return _resp(status, {"title": title, "status": status, "detail": detail,
                          "requestId": getattr(ctx, "aws_request_id", None)})


def _cursor_in(s):
    return json.loads(base64.urlsafe_b64decode(s.encode())) if s else None


def _cursor_out(k):
    return base64.urlsafe_b64encode(json.dumps(k, cls=_Enc).encode()).decode() if k else None


def _int(qs, name, default, lo, hi):
    try:
        v = int(qs.get(name, default))
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be an integer")
    return max(lo, min(hi, v))


def _vital_row(i):
    keys = ("ts", "seq", "hr", "hrMin", "hrMax", "sdnn", "spo2", "tempC", "activity", "flag",
            "reconError", "payloadBytes", "cloudVerdict", "edgeToIngestMs")
    return {k: i.get(k) for k in keys if k in i}


def list_devices(qs, claims):
    items = DEVICES.scan(Limit=200).get("Items", [])
    now = int(time.time() * 1000)
    for d in items:
        d["status"] = "online" if now - int(d.get("lastSeen", 0)) < ONLINE_WINDOW_MS else "offline"
    items.sort(key=lambda d: d["deviceId"])
    return _resp(200, {"devices": items})


def register_device(body, claims):
    dev = (body or {}).get("deviceId", "")
    if not DEVICE_RE.match(dev):
        raise ValueError("invalid deviceId")
    DEVICES.update_item(Key={"deviceId": dev},
                        UpdateExpression="SET label = :l, createdAt = if_not_exists(createdAt, :t)",
                        ExpressionAttributeValues={":l": body.get("label", dev), ":t": int(time.time() * 1000)})
    return _resp(201, {"deviceId": dev})


def vitals(dev, qs):
    now = int(time.time() * 1000)
    frm = _int(qs, "from", now - 3600_000, 0, now)
    to = _int(qs, "to", now, 0, now + 60_000)
    if frm >= to:
        raise ValueError("'from' must be before 'to'")
    kw = dict(KeyConditionExpression=Key("deviceId").eq(dev) & Key("ts").between(frm, to),
              Limit=_int(qs, "limit", 500, 1, 1000), ScanIndexForward=True)
    if qs.get("cursor"):
        kw["ExclusiveStartKey"] = _cursor_in(qs["cursor"])
    r = TELEMETRY.query(**kw)
    return _resp(200, {"deviceId": dev, "items": [_vital_row(i) for i in r.get("Items", [])],
                       "nextCursor": _cursor_out(r.get("LastEvaluatedKey"))})


def latest(dev):
    r = TELEMETRY.query(KeyConditionExpression=Key("deviceId").eq(dev), ScanIndexForward=False, Limit=1)
    items = r.get("Items", [])
    if not items:
        return _resp(404, {"title": "Not found", "status": 404, "detail": f"no data for {dev}"})
    return _resp(200, _vital_row(items[0]))


def stats(dev, qs):
    hours = _int(qs, "hours", 24, 1, 168)
    since = int(time.time() * 1000) - hours * 3600_000
    kw = dict(KeyConditionExpression=Key("deviceId").eq(dev) & Key("ts").gte(since),
              ProjectionExpression="flag, payloadBytes, edgeToIngestMs, cloudVerdict")
    flags = {"normal": 0, "suspect": 0, "critical": 0}
    verdicts = {}
    sent = 0
    lat = []
    while True:
        r = TELEMETRY.query(**kw)
        for i in r.get("Items", []):
            flags[i.get("flag", "normal")] = flags.get(i.get("flag", "normal"), 0) + 1
            sent += int(i.get("payloadBytes", 0))
            if "edgeToIngestMs" in i:
                lat.append(int(i["edgeToIngestMs"]))
            if "cloudVerdict" in i:
                verdicts[i["cloudVerdict"]] = verdicts.get(i["cloudVerdict"], 0) + 1
        if "LastEvaluatedKey" not in r:
            break
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    lat.sort()
    p = lambda q: lat[min(len(lat) - 1, int(q * len(lat)))] if lat else None  # noqa: E731
    windows = sum(flags.values())
    return _resp(200, {"deviceId": dev, "hours": hours, "windows": windows, "flags": flags,
                       "cloudVerdicts": verdicts, "uplinkBytes": sent,
                       "edgeToIngestMs": {"p50": p(0.5), "p95": p(0.95)}})


def alerts(qs):
    status = qs.get("status", "open")
    limit = _int(qs, "limit", 50, 1, 200)
    kw = {"Limit": limit, "ScanIndexForward": False}
    if qs.get("cursor"):
        kw["ExclusiveStartKey"] = _cursor_in(qs["cursor"])
    if qs.get("deviceId"):
        kw.update(IndexName="byDevice", KeyConditionExpression=Key("deviceId").eq(qs["deviceId"]))
        r = ALERTS.query(**kw)
        items = [i for i in r.get("Items", []) if status == "all" or i.get("status") == status]
    elif status == "all":
        items, last = [], None
        for st in ("open", "acknowledged"):
            r = ALERTS.query(IndexName="byStatus", KeyConditionExpression=Key("status").eq(st),
                             ScanIndexForward=False, Limit=limit)
            items += r.get("Items", [])
        items.sort(key=lambda a: a["ts"], reverse=True)
        items = items[:limit]
        r = {}
    else:
        kw.update(IndexName="byStatus", KeyConditionExpression=Key("status").eq(status))
        r = ALERTS.query(**kw)
        items = r.get("Items", [])
    return _resp(200, {"items": items, "nextCursor": _cursor_out(r.get("LastEvaluatedKey"))})


def ack(alert_id, body, claims):
    who = claims.get("email") or claims.get("username") or claims.get("sub", "unknown")
    try:
        ALERTS.update_item(
            Key={"alertId": alert_id},
            UpdateExpression="SET #s = :a, ackBy = :w, ackTs = :t, ackNote = :n",
            ConditionExpression="attribute_exists(alertId)",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":a": "acknowledged", ":w": who,
                                       ":t": int(time.time() * 1000), ":n": (body or {}).get("note", "")[:500]},
        )
    except _ddb.meta.client.exceptions.ConditionalCheckFailedException:
        return _resp(404, {"title": "Not found", "status": 404, "detail": "unknown alert"})
    return _resp(200, {"status": "acknowledged"})


def handler(event, context):
    route = event.get("routeKey", "")
    qs = event.get("queryStringParameters") or {}
    pp = event.get("pathParameters") or {}
    claims = (((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt") or {}).get("claims") or {}
    body = None
    if event.get("body"):
        raw = base64.b64decode(event["body"]) if event.get("isBase64Encoded") else event["body"]
        try:
            body = json.loads(raw)
        except ValueError:
            return _problem(400, "Bad request", "body must be JSON", context)
    try:
        if route == "GET /v1/health":
            return _resp(200, {"status": "ok", "version": VERSION})
        if route == "GET /v1/devices":
            return list_devices(qs, claims)
        if route == "POST /v1/devices":
            return register_device(body, claims)
        dev = pp.get("deviceId")
        if dev is not None and not DEVICE_RE.match(dev):
            raise ValueError("invalid deviceId")
        if route == "GET /v1/devices/{deviceId}/vitals":
            return vitals(dev, qs)
        if route == "GET /v1/devices/{deviceId}/vitals/latest":
            return latest(dev)
        if route == "GET /v1/devices/{deviceId}/stats":
            return stats(dev, qs)
        if route == "GET /v1/alerts":
            return alerts(qs)
        if route == "POST /v1/alerts/{alertId}/ack":
            return ack(pp.get("alertId", ""), body, claims)
        return _problem(404, "Not found", f"no route {route}", context)
    except ValueError as exc:
        return _problem(400, "Bad request", str(exc), context)
