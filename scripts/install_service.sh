#!/usr/bin/env bash
# Install and enable systemd services + create log directory.
# Run as root: sudo bash scripts/install_service.sh
set -euo pipefail

PROJ_DIR="/var/www/html/infobeans-agent-portal"
LOG_DIR="/var/log/infobeans"

echo "Creating log directory $LOG_DIR ..."
mkdir -p "$LOG_DIR"
chown www-data:www-data "$LOG_DIR"
chmod 750 "$LOG_DIR"

echo "Installing hub service ..."
cp "$PROJ_DIR/config/infobeans-agent-hub.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable infobeans-agent-hub
systemctl restart infobeans-agent-hub
systemctl status infobeans-agent-hub --no-pager

echo ""
echo "Done. Hub is running at http://127.0.0.1:8000"
echo "Point Nginx to that address and reload: sudo nginx -t && sudo systemctl reload nginx"
