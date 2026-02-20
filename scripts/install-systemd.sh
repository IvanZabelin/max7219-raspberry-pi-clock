#!/usr/bin/env bash
set -euo pipefail

SERVICE_SRC="deploy/systemd/led-clock.service"
ENV_EXAMPLE_SRC="deploy/systemd/led-clock.env.example"
SERVICE_DST="/etc/systemd/system/led-clock.service"
ENV_DST="/etc/default/led-clock"

if [[ ! -f "$SERVICE_SRC" ]]; then
  echo "[ERR] $SERVICE_SRC not found"
  exit 1
fi

sudo cp "$SERVICE_SRC" "$SERVICE_DST"

if [[ ! -f "$ENV_DST" ]]; then
  sudo cp "$ENV_EXAMPLE_SRC" "$ENV_DST"
  echo "[OK] Created $ENV_DST from example"
else
  echo "[OK] Keeping existing $ENV_DST"
fi

sudo systemctl daemon-reload
sudo systemctl enable led-clock.service
sudo systemctl restart led-clock.service

echo "[OK] Service installed and restarted"
echo "Check: sudo systemctl status led-clock.service"
echo "Logs : sudo journalctl -u led-clock.service -f"
