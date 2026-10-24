#!/usr/bin/env bash
# Live demo data source: streams simulated wearable windows to AWS IoT Core
# with the demo-001 device certificate (mutual TLS on port 443).
# Each window is scored on the Mac by the trained ONNX autoencoder.
#   ./run_demo.sh                    healthy stream, one window every 3 s (Ctrl+C to stop)
#   ./run_demo.sh tachycardia 3      send 3 abnormal windows -> confirmed alert + email
#   profiles: healthy | mixed | tachycardia | bradycardia | arrhythmia | hypoxia
set -e
cd "$(dirname "$0")/edge"
if [ ! -d .venv ]; then
  echo "first run: installing Python packages (about a minute)…"
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q numpy scipy awsiotsdk
fi
.venv/bin/python -c "import onnxruntime" 2>/dev/null || { echo "installing onnxruntime…"; .venv/bin/pip install -q onnxruntime; }
PROFILE="${1:-healthy}"
WINDOWS="${2:-}"
EP="$(cat config/certs/demo-001/endpoint.txt)"
.venv/bin/python -m simulator.run --device-id demo-001 --profile "$PROFILE" \
  ${WINDOWS:+--windows "$WINDOWS"} --interval 3 \
  --endpoint "$EP" --cert-dir config/certs/demo-001
