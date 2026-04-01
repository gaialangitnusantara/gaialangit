#!/bin/bash
# init_db.sh — Create the Gaialangit database and install base modules
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

source "$PROJECT_DIR/.env" 2>/dev/null || true

DB_NAME="${ODOO_DB:-gaialangit}"
ODOO_CONTAINER="gaialangit-odoo"

echo "=== Initializing database: $DB_NAME ==="

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "$ODOO_CONTAINER"; then
    echo "[ERROR] Odoo container is not running. Run ./scripts/start_odoo.sh first."
    exit 1
fi

# Create database and install base modules
# This installs: base, stock, purchase, purchase_stock, sale_management,
#                account, stock_account, mail
# l10n_id is installed with account for Indonesian localization
echo "Creating database and installing standard modules..."
echo "This may take several minutes on first run."

docker exec -u odoo "$ODOO_CONTAINER" \
    odoo -d "$DB_NAME" \
    -i base,mail,stock,purchase,purchase_stock,sale_management,account,stock_account,l10n_id \
    --without-demo=all \
    --stop-after-init \
    --no-http

echo ""
echo "[OK] Database '$DB_NAME' initialized with standard modules."
echo ""
echo "Next steps:"
echo "  1. Restart Odoo: ./scripts/start_odoo.sh"
echo "  2. Open http://localhost:${ODOO_PORT:-8069}"
echo "  3. Login with admin / admin"
echo "  4. Configure company, warehouse, and chart of accounts"
echo "  5. Create duck products (see docs/prd.md section 5)"
