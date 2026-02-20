#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
PROFILES_DIR="config/profiles"
TARGET_ENV="/etc/default/led-clock"

if [[ -z "$MODE" ]]; then
  echo "Usage: $0 <clock|status|info>"
  exit 1
fi

SRC="$PROFILES_DIR/$MODE.env"
if [[ ! -f "$SRC" ]]; then
  echo "[ERR] Profile not found: $SRC"
  echo "Available profiles:"
  ls -1 "$PROFILES_DIR" | sed 's/\.env$//'
  exit 1
fi

sudo cp "$SRC" "$TARGET_ENV"
sudo systemctl restart led-clock.service

echo "[OK] Switched mode to '$MODE'"
echo "[OK] Active env: $TARGET_ENV"
echo "[OK] Check logs: tail -n 30 /var/log/led-clock.log"
