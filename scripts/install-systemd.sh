#!/usr/bin/env bash
set -euo pipefail

SERVICE_SRC="deploy/systemd/led-clock.service"
ENV_EXAMPLE_SRC="deploy/systemd/led-clock.env.example"
LOGROTATE_SRC="deploy/logrotate/led-clock"
SERVICE_DST="/etc/systemd/system/led-clock.service"
ENV_DST="/etc/default/led-clock"
LOGROTATE_DST="/etc/logrotate.d/led-clock"

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

sudo touch /var/log/led-clock.log
sudo chown theza:theza /var/log/led-clock.log
sudo cp "$LOGROTATE_SRC" "$LOGROTATE_DST"

sudo systemctl daemon-reload
sudo systemctl enable led-clock.service
sudo systemctl restart led-clock.service

echo "[OK] Service installed and restarted"
echo "Check: sudo systemctl status led-clock.service"
echo "Logs : tail -f /var/log/led-clock.log"
echo "Also : sudo journalctl -u led-clock.service -f"
