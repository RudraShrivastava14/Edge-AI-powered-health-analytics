"""MQTT over WebSocket to AWS IoT Core, authenticated with SigV4 (IAM credentials).

Used for development machines and CI runners where an outbound HTTPS proxy terminates TLS,
which makes X.509 mutual TLS impossible. Production gateways use the mTLS path in run.py.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.parse


def _presign(endpoint: str, region: str) -> str:
    import boto3
    from botocore.auth import SigV4QueryAuth
    from botocore.awsrequest import AWSRequest

    creds = boto3.Session().get_credentials().get_frozen_credentials()
    req = AWSRequest(method="GET", url=f"https://{endpoint}/mqtt")
    SigV4QueryAuth(creds._replace(token=None) if creds.token else creds, "iotdevicegateway",
                   region, expires=86400).add_auth(req)
    path = urllib.parse.urlsplit(req.url)
    query = path.query
    if creds.token:  # IoT wants the session token appended *after* signing
        query += "&X-Amz-Security-Token=" + urllib.parse.quote(creds.token, safe="")
    return f"/mqtt?{query}"


def connect_wss(endpoint: str, region: str, client_id: str):
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, transport="websockets")
    client.ws_set_options(path=_presign(endpoint, region))
    client.tls_set(ca_certs=os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE"))
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        import socks
        u = urllib.parse.urlsplit(proxy)
        client.proxy_set(proxy_type=socks.HTTP, proxy_addr=u.hostname, proxy_port=u.port)
    ready = threading.Event()
    client.on_connect = lambda c, u, f, rc, p=None: ready.set()
    print(f"connecting to {endpoint} over WSS as {client_id} …", flush=True)
    client.connect(endpoint, 443, keepalive=30)
    client.loop_start()
    if not ready.wait(20):
        raise SystemExit("MQTT connection timed out")
    print("connected", flush=True)

    def publish(topic, payload, qos=0):
        info = client.publish(topic, json.dumps(payload, separators=(",", ":")), qos=qos)
        if qos:
            info.wait_for_publish(10)
        return True

    return publish
