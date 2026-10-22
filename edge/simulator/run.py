"""Edge simulator CLI.

Generates synthetic vital-sign windows, runs the edge scoring + uplink policy, and either
prints the resulting payloads (``--dry-run``) or publishes them to AWS IoT Core over MQTT.

Examples
--------
    # offline, costs nothing, no AWS account needed
    python -m simulator.run --device-id demo-001 --profile mixed --dry-run --windows 20

    # live against the deployed stack
    python -m simulator.run --device-id demo-001 --profile arrhythmia \
        --endpoint xxxx-ats.iot.ap-south-1.amazonaws.com \
        --cert-dir config/certs/demo-001
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

# Allow `python simulator/run.py` as well as `python -m simulator.run`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from edge_inference import policy  # noqa: E402
from simulator.generator import PROFILES, generate_stream  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Wearable telemetry simulator")
    p.add_argument("--device-id", required=True, help="opaque device identifier")
    p.add_argument("--profile", default="mixed",
                   choices=[*sorted(PROFILES), "mixed"],
                   help="physiological profile to simulate")
    p.add_argument("--windows", type=int, default=None,
                   help="number of 10 s windows (default: run forever)")
    p.add_argument("--interval", type=float, default=10.0,
                   help="seconds between publishes; lower it to compress a demo")
    p.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    p.add_argument("--dry-run", action="store_true",
                   help="print payloads instead of publishing (no AWS, no cost)")
    p.add_argument("--endpoint", help="AWS IoT ATS data endpoint")
    p.add_argument("--cert-dir", help="directory holding certificate.pem, private.key, AmazonRootCA1.pem")
    p.add_argument("--topic-prefix", default="hh/v1")
    p.add_argument("--transport", choices=["mtls", "wss"], default="mtls",
                   help="mtls: X.509 device certificate (real devices); wss: MQTT over WebSocket "
                        "signed with the caller's IAM credentials (development, behind proxies)")
    p.add_argument("--region", default="ap-south-1")
    p.add_argument("--verbose", "-v", action="store_true", help="print each payload in full")
    return p.parse_args(argv)


def make_publisher(args):
    """Return a ``publish(topic, payload_dict, qos)`` callable."""
    if args.dry_run:
        def publish(topic, payload, qos=0):
            if args.verbose:
                print(json.dumps(payload, indent=2)[:2000])
            return True
        return publish

    if args.transport == "wss":
        if not args.endpoint:
            sys.exit("--endpoint is required for --transport wss")
        from simulator.wss import connect_wss
        return connect_wss(args.endpoint, args.region, args.device_id)

    if not (args.endpoint and args.cert_dir):
        sys.exit("--endpoint and --cert-dir are required unless --dry-run is set")

    # Imported lazily so --dry-run works without the AWS SDK installed.
    from awscrt import mqtt  # noqa: F401
    from awsiot import mqtt_connection_builder

    certs = pathlib.Path(args.cert_dir)
    conn = mqtt_connection_builder.mtls_from_path(
        endpoint=args.endpoint,
        cert_filepath=str(certs / "certificate.pem"),
        pri_key_filepath=str(certs / "private.key"),
        ca_filepath=str(certs / "AmazonRootCA1.pem"),
        client_id=args.device_id,
        clean_session=False,
        keep_alive_secs=30,
    )
    print(f"connecting to {args.endpoint} as {args.device_id} …", flush=True)
    conn.connect().result()
    print("connected", flush=True)

    def publish(topic, payload, qos=0):
        from awscrt import mqtt as _mqtt
        level = _mqtt.QoS.AT_LEAST_ONCE if qos else _mqtt.QoS.AT_MOST_ONCE
        conn.publish(topic=topic, payload=json.dumps(payload, separators=(",", ":")), qos=level)
        return True

    return publish


def main(argv=None) -> int:
    args = parse_args(argv)
    publish = make_publisher(args)
    topic = f"{args.topic_prefix}/{args.device_id}/telemetry"
    thresholds = policy.Thresholds()

    # Counters for bandwidth benchmark E5.
    sent_bytes = baseline_total = 0
    flag_counts = {f.value: 0 for f in policy.Flag}
    seq = 0
    started = time.time()

    print(f"device={args.device_id} profile={args.profile} topic={topic} "
          f"{'(dry run)' if args.dry_run else ''}", flush=True)

    try:
        for window in generate_stream(args.profile, n_windows=args.windows, seed=args.seed):
            seq += 1
            recon_error, inference_ms = policy.score_window(window)
            flag = policy.classify(recon_error, window.activity, thresholds)
            payload = policy.build_payload(
                device_id=args.device_id,
                ts_ms=int(time.time() * 1000),
                seq=seq,
                window=window,
                recon_error=recon_error,
                flag=flag,
                inference_ms=inference_ms,
            )

            size = policy.payload_bytes(payload)
            sent_bytes += size
            baseline_total += policy.baseline_bytes(window)
            flag_counts[flag.value] += 1

            publish(topic, payload, qos=1 if flag is policy.Flag.CRITICAL else 0)

            hr = payload["vitals"]["hr"]["mean"]
            print(f"[{seq:>5}] {window.profile:<12} act={window.activity:<4} "
                  f"hr={hr:6.1f} spo2={window.spo2:5.1f} e={recon_error:.4f} "
                  f"flag={flag.value:<8} {size:>6} B", flush=True)

            if args.windows is None or seq < args.windows:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\ninterrupted", flush=True)

    elapsed = time.time() - started
    reduction = (1 - sent_bytes / baseline_total) * 100 if baseline_total else 0.0
    print("\n--- summary " + "-" * 48)
    print(f"windows            : {seq}")
    print(f"elapsed            : {elapsed:.1f} s")
    print(f"flags              : {flag_counts}")
    print(f"uplink sent        : {sent_bytes:,} B")
    print(f"stream-all baseline: {baseline_total:,} B")
    print(f"reduction          : {reduction:.1f} %   (target >= 90 %)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
