"""alert_dispatcher — de-duplicate, debounce and publish confirmed alerts to SNS.

A sustained episode produces a confirmed alert every 10 seconds; a clinician needs one
notification, not thirty. An alert is suppressed when the same device already sent a
notification of equal or higher severity within DEBOUNCE_SECONDS. Every alert stays in the table either way, so the
dashboard timeline is complete. End-to-end latency (edge timestamp -> SNS publish) is
recorded on the alert for benchmarking.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Attr, Key

_ddb = boto3.resource("dynamodb")
_sns = boto3.client("sns")

ALERTS = _ddb.Table(os.environ["ALERTS_TABLE"])
TOPIC_ARN = os.environ["ALERTS_TOPIC_ARN"]
DEBOUNCE_S = int(os.environ.get("DEBOUNCE_SECONDS", "300"))
IST = timezone(timedelta(hours=5, minutes=30))

LABELS = {
    "tachycardia": "Tachycardia (high heart rate)",
    "bradycardia": "Bradycardia (low heart rate)",
    "desaturation": "SpO2 desaturation",
    "irregular_rhythm": "Irregular heart rhythm",
    "ventricular_ectopy": "Ventricular ectopic beats (PVCs)",
    "supraventricular_ectopy": "Supraventricular ectopic beats",
}


def _recent_notified(alert: dict) -> bool:
    since = int(alert["ts"]) - DEBOUNCE_S * 1000
    resp = ALERTS.query(
        IndexName="byDevice",
        KeyConditionExpression=Key("deviceId").eq(alert["deviceId"]) & Key("ts").between(since, int(alert["ts"])),
        FilterExpression=Attr("notified").eq(True) & Attr("alertId").ne(alert["alertId"]),
    )
    rank = {"medium": 1, "high": 2}
    # One email per device per episode; a new email only if the situation escalates.
    return any(rank.get(i.get("severity"), 0) >= rank.get(alert.get("severity"), 0) for i in resp.get("Items", []))


def handler(event, context):
    alert = ALERTS.get_item(Key={"alertId": event["alertId"]}).get("Item")
    if not alert:
        return {"status": "missing"}

    if _recent_notified(alert):
        ALERTS.update_item(Key={"alertId": alert["alertId"]},
                           UpdateExpression="SET notified = :f, suppressedReason = :r",
                           ExpressionAttributeValues={":f": False, ":r": f"debounced ({DEBOUNCE_S}s)"})
        print(json.dumps({"level": "INFO", "alertId": alert["alertId"], "action": "suppressed"}))
        return {"status": "suppressed"}

    when = datetime.fromtimestamp(int(alert["ts"]) / 1000, tz=IST).strftime("%d %b %Y, %H:%M:%S IST")
    label = LABELS.get(alert["class"], alert["class"])
    lines = [
        f"{label} detected on device {alert['deviceId']}",
        "",
        f"Time:        {when}",
        f"Severity:    {alert['severity']}",
        f"Confidence:  {alert.get('confidence')}",
        f"Heart rate:  {alert.get('hr')} bpm (from ECG: {alert.get('hrEcg') or 'n/a'})",
        f"SpO2:        {alert.get('spo2')} %",
        f"Activity:    {alert.get('activity')}",
        f"Edge flag:   {alert.get('edgeFlag')} (edge model {alert.get('edgeModel')}, score {alert.get('edgeReconError')})",
        f"Cloud model: {alert.get('cloudModel')} - {alert.get('beats')} beats classified {alert.get('beatCounts')}",
        "",
        f"Alert ID: {alert['alertId']}",
        "Open the dashboard to review the waveform and acknowledge.",
        "",
        "Academic prototype - not a medical device.",
    ]
    _sns.publish(TopicArn=TOPIC_ARN, Subject=f"[HealthEdge] {label} - {alert['deviceId']}"[:100],
                 Message="\n".join(lines))
    now = int(time.time() * 1000)
    latency = now - int(alert["ts"])
    ALERTS.update_item(Key={"alertId": alert["alertId"]},
                       UpdateExpression="SET notified = :t, notifiedTs = :n, endToEndMs = :l",
                       ExpressionAttributeValues={":t": True, ":n": now, ":l": latency})
    print(json.dumps({"level": "INFO", "alertId": alert["alertId"], "action": "published",
                      "endToEndMs": latency}))
    return {"status": "published", "endToEndMs": latency}
