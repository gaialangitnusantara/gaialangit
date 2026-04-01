#!/bin/bash
# stop_odoo.sh — Stop the Odoo + PostgreSQL stack
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Stopping Gaialangit ERP ==="
docker compose down

echo "[OK] Stack stopped."
