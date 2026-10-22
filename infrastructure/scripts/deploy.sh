#!/usr/bin/env bash
# One-command deploy: backend stack + dashboard upload.
#   ALERT_EMAIL=you@example.com infrastructure/scripts/deploy.sh [dev|prod]
set -euo pipefail
# Ignore any ambient placeholder credentials; use the configured profile/key file.
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
ENV="${1:-dev}"
REGION="${AWS_REGION:-ap-south-1}"
STACK="hh-${ENV}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ALERT_EMAIL="${ALERT_EMAIL:-}"

echo "==> deploying stack ${STACK} to ${REGION}"
sam deploy \
  --template-file "${ROOT}/infrastructure/template.yaml" \
  --stack-name "${STACK}" --region "${REGION}" \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --resolve-s3 --no-confirm-changeset --no-fail-on-empty-changeset \
  --parameter-overrides "Env=${ENV}" "AlertEmail=${ALERT_EMAIL}" "EnableCloudFront=${ENABLE_CLOUDFRONT:-true}" \
  --tags project=health-analytics env="${ENV}"

aws cloudformation describe-stacks --stack-name "${STACK}" --region "${REGION}" \
  --query 'Stacks[0].Outputs' --output json > "${ROOT}/infrastructure/.outputs-${ENV}.json"
out() { python3 -c "import json,sys;print(next((o['OutputValue'] for o in json.load(open(sys.argv[1])) if o['OutputKey']==sys.argv[2]),''))" "${ROOT}/infrastructure/.outputs-${ENV}.json" "$1"; }

echo "==> building dashboard"
cd "${ROOT}/frontend"
[ -d node_modules ] || npm ci --no-audit --no-fund
npx vite build >/dev/null
cat > dist/config.json <<JSON
{ "region": "${REGION}", "apiEndpoint": "$(out ApiEndpoint)", "userPoolId": "$(out UserPoolId)",
  "userPoolClientId": "$(out UserPoolClientId)", "pollMs": 5000 }
JSON
WEB="$(out WebBucketName)"
aws s3 sync dist/ "s3://${WEB}/" --delete --region "${REGION}" \
  --cache-control "public,max-age=31536000,immutable" --exclude index.html --exclude config.json --exclude README.md
aws s3 cp dist/index.html "s3://${WEB}/index.html" --region "${REGION}" --cache-control "no-cache"
aws s3 cp dist/config.json "s3://${WEB}/config.json" --region "${REGION}" --cache-control "no-cache"
DIST="$(out DistributionId)"
[ -n "${DIST}" ] && aws cloudfront create-invalidation --distribution-id "${DIST}" --paths "/index.html" "/config.json" >/dev/null
echo "==> done. Dashboard: $(out DashboardUrl)   API: $(out ApiEndpoint)"
