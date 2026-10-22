#!/usr/bin/env bash
# Tear everything down (buckets are emptied first so the stack can delete them).
#   infrastructure/scripts/destroy.sh [dev|prod]
set -euo pipefail
ENV="${1:-dev}"; REGION="${AWS_REGION:-ap-south-1}"; STACK="hh-${ENV}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
for b in "hh-${ENV}-raw-${ACCOUNT}-${REGION}" "hh-${ENV}-web-${ACCOUNT}-${REGION}"; do
  aws s3 rm "s3://${b}" --recursive --region "${REGION}" 2>/dev/null || true
done
# IoT things/certificates are created outside CloudFormation (keys must never sit in a template).
python3 "$(dirname "$0")/provision_device.py" --env "${ENV}" --region "${REGION}" --delete-all || true
aws cloudformation delete-stack --stack-name "${STACK}" --region "${REGION}"
aws cloudformation wait stack-delete-complete --stack-name "${STACK}" --region "${REGION}"
echo "stack ${STACK} deleted"
