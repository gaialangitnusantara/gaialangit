#!/bin/bash
# upgrade_addon.sh — Upgrade an installed custom addon
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

source "$PROJECT_DIR/.env" 2>/dev/null || true

DB_NAME="${ODOO_DB:-gaialangit}"
ODOO_CONTAINER="gaialangit-odoo"
ADDON_NAME="${1:-}"

if [ -z "$ADDON_NAME" ]; then
    echo "Usage: ./scripts/upgrade_addon.sh <addon_name>"
    echo "Example: ./scripts/upgrade_addon.sh agri_duck_ops"
    exit 1
fi

echo "=== Upgrading addon: $ADDON_NAME ==="

docker exec -u odoo "$ODOO_CONTAINER" \
    odoo -d "$DB_NAME" \
    -u "$ADDON_NAME" \
    --stop-after-init \
    --no-http

echo ""
echo "[OK] Addon '$ADDON_NAME' upgraded successfully."
echo "     Restart Odoo to load: ./scripts/start_odoo.sh"
