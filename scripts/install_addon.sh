#!/bin/bash
# install_addon.sh — Install a custom addon into the Gaialangit database
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

source "$PROJECT_DIR/.env" 2>/dev/null || true

DB_NAME="${ODOO_DB:-gaialangit}"
ODOO_CONTAINER="gaialangit-odoo"
ADDON_NAME="${1:-}"

if [ -z "$ADDON_NAME" ]; then
    echo "Usage: ./scripts/install_addon.sh <addon_name>"
    echo "Example: ./scripts/install_addon.sh agri_base_masterdata"
    exit 1
fi

# Verify addon exists in addons directory
if [ ! -d "$PROJECT_DIR/addons/$ADDON_NAME" ]; then
    echo "[ERROR] Addon '$ADDON_NAME' not found in addons/ directory."
    echo "Available addons:"
    ls -d "$PROJECT_DIR/addons"/*/ 2>/dev/null | xargs -I{} basename {} || echo "  (none)"
    exit 1
fi

# Verify __manifest__.py exists
if [ ! -f "$PROJECT_DIR/addons/$ADDON_NAME/__manifest__.py" ]; then
    echo "[ERROR] No __manifest__.py found in addons/$ADDON_NAME/"
    exit 1
fi

echo "=== Installing addon: $ADDON_NAME ==="

docker exec -u odoo "$ODOO_CONTAINER" \
    odoo -d "$DB_NAME" \
    -i "$ADDON_NAME" \
    --stop-after-init \
    --no-http

echo ""
echo "[OK] Addon '$ADDON_NAME' installed successfully."
echo "     Restart Odoo to load: ./scripts/start_odoo.sh"
