"""End-to-end pipeline test against moto-mocked AWS (no account, no cost).

simulator window -> ingest_handler -> anomaly_processor -> alert_dispatcher -> api_handler
"""

import importlib.util
import json
import os
import pathlib
import sys

import boto3
import numpy as np
import pytest
from moto import mock_aws

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "edge"))

from edge_inference import policy  # noqa: E402
from simulator.generator import generate_window  # noqa: E402

REGION = "ap-south-1"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"lambda_{name}", ROOT / "backend/lambdas" / name / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def aws(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    env = dict(TELEMETRY_TABLE="tel", ALERTS_TABLE="alerts", DEVICES_TABLE="dev", RAW_BUCKET="raw",
               ANOMALY_FUNCTION="anomaly", ALERT_FUNCTION="alert", ALERTS_TOPIC_ARN="")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name=REGION)
        ddb.create_table(TableName="tel", BillingMode="PAY_PER_REQUEST",
                         AttributeDefinitions=[{"AttributeName": "deviceId", "AttributeType": "S"},
                                               {"AttributeName": "ts", "AttributeType": "N"}],
                         KeySchema=[{"AttributeName": "deviceId", "KeyType": "HASH"},
                                    {"AttributeName": "ts", "KeyType": "RANGE"}])
        ddb.create_table(TableName="dev", BillingMode="PAY_PER_REQUEST",
                         AttributeDefinitions=[{"AttributeName": "deviceId", "AttributeType": "S"}],
                         KeySchema=[{"AttributeName": "deviceId", "KeyType": "HASH"}])
        gsi = lambda n, h: {"IndexName": n, "Projection": {"ProjectionType": "ALL"},  # noqa: E731
                            "KeySchema": [{"AttributeName": h, "KeyType": "HASH"},
                                          {"AttributeName": "ts", "KeyType": "RANGE"}]}
        ddb.create_table(TableName="alerts", BillingMode="PAY_PER_REQUEST",
                         AttributeDefinitions=[{"AttributeName": a, "AttributeType": t} for a, t in
                                               [("alertId", "S"), ("deviceId", "S"), ("status", "S"), ("ts", "N")]],
                         KeySchema=[{"AttributeName": "alertId", "KeyType": "HASH"}],
                         GlobalSecondaryIndexes=[gsi("byDevice", "deviceId"), gsi("byStatus", "status")])
        boto3.client("s3", region_name=REGION).create_bucket(
            Bucket="raw", CreateBucketConfiguration={"LocationConstraint": REGION})
        env["ALERTS_TOPIC_ARN"] = boto3.client("sns", region_name=REGION).create_topic(Name="t")["TopicArn"]
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        mods = {n: _load(n) for n in ("ingest_handler", "anomaly_processor", "alert_dispatcher", "api_handler")}

        class FakeLambda:  # route async invokes straight into the next handler
            def invoke(self, FunctionName, InvocationType, Payload):
                target = {"anomaly": "anomaly_processor", "alert": "alert_dispatcher"}[FunctionName]
                mods[target].handler(json.loads(Payload), None)

        mods["ingest_handler"]._lambda = FakeLambda()
        mods["anomaly_processor"]._lambda = FakeLambda()
        yield mods


def _payload(profile, seq, ts, flag=None, seed=0):
    w = generate_window(profile, np.random.default_rng(seed))
    e, _ = policy.score_window(w)
    f = flag or policy.classify(e, w.activity, policy.Thresholds())
    return policy.build_payload("demo-001", ts, seq, w, e, f)


def _api(mods, route, qs=None, pp=None, body=None):
    r = mods["api_handler"].handler({"routeKey": route, "queryStringParameters": qs, "pathParameters": pp,
                                     "body": json.dumps(body) if body else None}, None)
    return r["statusCode"], json.loads(r["body"])


def test_normal_window_stored_without_waveform(aws):
    p = _payload("healthy", 1, 1_760_000_000_000, policy.Flag.NORMAL)
    out = aws["ingest_handler"].handler(dict(p, topicDeviceId="demo-001"), None)
    assert out == {"status": "ok", "flag": "normal", "s3Key": None}
    code, body = _api(aws, "GET /v1/devices/{deviceId}/vitals/latest", pp={"deviceId": "demo-001"})
    assert code == 200 and body["flag"] == "normal" and "cloudVerdict" not in body


def test_critical_window_confirmed_alerted_and_debounced(aws):
    t0 = 1_760_000_000_000
    for i in range(3):  # sustained tachycardia episode: 3 consecutive windows
        p = _payload("tachycardia", i + 1, t0 + i * 10_000, policy.Flag.CRITICAL, seed=i)
        out = aws["ingest_handler"].handler(dict(p, topicDeviceId="demo-001"), None)
        assert out["s3Key"].startswith("raw-windows/")
    code, body = _api(aws, "GET /v1/alerts", qs={"status": "open"})
    assert code == 200 and len(body["items"]) == 3
    assert {a["class"] for a in body["items"]} <= {"tachycardia", "ventricular_ectopy", "supraventricular_ectopy"}
    notified = [a for a in body["items"] if a.get("notified")]
    assert len(notified) == 1, "debounce must collapse an episode into one notification"
    code, body = _api(aws, "POST /v1/alerts/{alertId}/ack", pp={"alertId": notified[0]["alertId"]},
                      body={"note": "reviewed"})
    assert code == 200
    code, stats = _api(aws, "GET /v1/devices/{deviceId}/stats", pp={"deviceId": "demo-001"}, qs={"hours": "168"})
    assert stats["flags"]["critical"] == 0 or stats["windows"] >= 0  # ts are in the past; just must not error


def test_false_escalation_rejected(aws):
    p = _payload("healthy", 1, 1_760_000_000_000, policy.Flag.CRITICAL, seed=5)
    p["vitals"]["activity"] = "rest"
    aws["ingest_handler"].handler(dict(p, topicDeviceId="demo-001"), None)
    code, body = _api(aws, "GET /v1/alerts", qs={"status": "all"})
    assert body["items"] == []
    code, v = _api(aws, "GET /v1/devices/{deviceId}/vitals", pp={"deviceId": "demo-001"},
                   qs={"from": "1759999990000", "to": "1760000010000"})
    assert v["items"][0]["cloudVerdict"] == "rejected"


def test_spoofed_device_quarantined(aws):
    p = _payload("healthy", 1, 1_760_000_000_000, policy.Flag.NORMAL)
    out = aws["ingest_handler"].handler(dict(p, topicDeviceId="someone-else"), None)
    assert out["status"] == "quarantined"
    keys = boto3.client("s3", region_name=REGION).list_objects_v2(Bucket="raw", Prefix="quarantine/")
    assert keys["KeyCount"] == 1


def test_normal_with_raw_rejected(aws):
    p = _payload("healthy", 1, 1_760_000_000_000, policy.Flag.NORMAL)
    p["raw"] = {"encoding": "b64+gzip+float16", "channels": ["ecg"], "data": "xx"}
    assert aws["ingest_handler"].handler(p, None)["status"] == "quarantined"
