#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   sudo bash deploy/oracle/bootstrap.sh <repo_url> [branch]
#
# Example:
#   sudo bash deploy/oracle/bootstrap.sh https://github.com/you/manik_bot.git main

REPO_URL="${1:-}"
BRANCH="${2:-main}"
APP_USER="manikbot"
APP_DIR="/opt/manik_bot"
PY_VENV="$APP_DIR/.venv"
SERVICE_NAME="manik-bot"

if [[ -z "$REPO_URL" ]]; then
  echo "ERROR: pass repo URL as first argument."
  echo "Example: sudo bash deploy/oracle/bootstrap.sh https://github.com/you/manik_bot.git main"
  exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)."
  exit 1
fi

apt-get update
apt-get install -y git python3 python3-venv python3-pip

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$APP_USER"
fi

mkdir -p /opt
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
fi

python3 -m venv "$PY_VENV"
"$PY_VENV/bin/pip" install --upgrade pip
"$PY_VENV/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "Created $APP_DIR/.env from template. Fill BOT_TOKEN/ADMIN_ID/CHANNEL_ID/CHANNEL_LINK."
fi

mkdir -p "$APP_DIR/database"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

cat >/etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Telegram bot manik_bot
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$PY_VENV/bin/python $APP_DIR/bot.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo
echo "Done."
echo "1) Edit env: sudo nano $APP_DIR/.env"
echo "2) Restart:  sudo systemctl restart $SERVICE_NAME"
echo "3) Logs:     sudo journalctl -u $SERVICE_NAME -f"
