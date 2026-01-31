#!/usr/bin/env bash
set -euo pipefail

# Log everything
exec > >(tee -a /var/log/reboot-script.log) 2>&1
echo "=== reboot_script started: $(date -Is) ==="

MOUNT_DIR="${MOUNT_DIR:-/mnt}"
APP_DIR="${MOUNT_DIR}/code"

# Start services
cd "$APP_DIR"

docker compose up -d

echo "=== Reboot complete: $(date -Is) ==="
