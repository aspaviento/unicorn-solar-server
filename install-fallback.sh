#!/bin/bash

set -e

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"

sudo apt-get install -y python3-pip python3-dev python3-venv
python3 -m venv --system-site-packages "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

sudo cp "$INSTALL_DIR/unicorn-solar.service" /etc/systemd/system/unicorn-solar.service
sudo systemctl daemon-reload
if systemctl list-unit-files busylight.service > /dev/null 2>&1; then
    sudo systemctl disable --now busylight.service
fi
sudo systemctl enable --now unicorn-solar.service

sudo chmod +x "$INSTALL_DIR/start.sh"
