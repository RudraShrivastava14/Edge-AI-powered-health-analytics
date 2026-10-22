"""Register a simulated/real device in AWS IoT Core.

Creates the Thing, an X.509 certificate + key pair, attaches the stack's device policy
(which only allows the device to use its own topics) and writes the credentials to
edge/config/certs/<deviceId>/ (git-ignored).

    python infrastructure/scripts/provision_device.py --device-id demo-001
    python infrastructure/scripts/provision_device.py --delete-all      # teardown
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import ssl

import boto3

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device-id")
    ap.add_argument("--label")
    ap.add_argument("--env", default="dev")
    ap.add_argument("--region", default="ap-south-1")
    ap.add_argument("--delete-all", action="store_true")
    a = ap.parse_args()
    iot = boto3.client("iot", region_name=a.region)
    policy = f"hh-{a.env}-device-policy"
    group_attr = {"attributes": {"project": "health-analytics", "env": a.env}}

    if a.delete_all:
        for t in iot.list_things(attributeName="project", attributeValue="health-analytics")["things"]:
            name = t["thingName"]
            for p in iot.list_thing_principals(thingName=name)["principals"]:
                iot.detach_thing_principal(thingName=name, principal=p)
                cert_id = p.split("/")[-1]
                try:
                    iot.detach_policy(policyName=policy, target=p)
                except iot.exceptions.ResourceNotFoundException:
                    pass
                iot.update_certificate(certificateId=cert_id, newStatus="INACTIVE")
                iot.delete_certificate(certificateId=cert_id, forceDelete=True)
            iot.delete_thing(thingName=name)
            print("deleted", name)
        return

    dev = a.device_id
    iot.create_thing(thingName=dev, attributePayload=group_attr)
    cert = iot.create_keys_and_certificate(setAsActive=True)
    iot.attach_policy(policyName=policy, target=cert["certificateArn"])
    iot.attach_thing_principal(thingName=dev, principal=cert["certificateArn"])
    out = ROOT / "edge/config/certs" / dev
    out.mkdir(parents=True, exist_ok=True)
    (out / "certificate.pem").write_text(cert["certificatePem"])
    (out / "private.key").write_text(cert["keyPair"]["PrivateKey"])
    (out / "private.key").chmod(0o600)
    ca = pathlib.Path(ssl.get_default_verify_paths().openssl_cafile or "")
    bundled = pathlib.Path("/etc/ssl/certs/Amazon_Root_CA_1.pem")
    if bundled.exists():
        shutil.copy(bundled, out / "AmazonRootCA1.pem")
    endpoint = iot.describe_endpoint(endpointType="iot:Data-ATS")["endpointAddress"]
    (out / "endpoint.txt").write_text(endpoint + "\n")
    print(f"provisioned {dev}: cert {cert['certificateId'][:12]}…  endpoint {endpoint}  -> {out}")


if __name__ == "__main__":
    main()
