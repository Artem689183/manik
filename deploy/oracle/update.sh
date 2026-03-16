#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   sudo bash deploy/oracle/update.sh [branch]
#
# Example:
#   sudo bash deploy/oracle/update.sh main

BRANCH="${1:-main}"
APP_DIR="/opt/manik_bot"
VENV_BIN="$APP_DIR/.venv/bin"
SERVICE_NAME="manik-bot"
APP_USER="manikbot"

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)."
  exit 1
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "ERROR: repo not found in $APP_DIR"
  exit 1
fi

git -C "$APP_DIR" fetch origin
git -C "$APP_DIR" checkout "$BRANCH"
git -C "$APP_DIR" pull --ff-only origin "$BRANCH"

"$VENV_BIN/pip" install --upgrade pip
"$VENV_BIN/pip" install -r "$APP_DIR/requirements.txt"

chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
systemctl restart "$SERVICE_NAME"

echo "Updated and restarted $SERVICE_NAME"
