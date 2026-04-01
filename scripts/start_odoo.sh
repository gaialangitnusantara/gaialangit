#!/bin/bash
# start_odoo.sh — Start the Odoo + PostgreSQL stack
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Starting Gaialangit ERP ==="
docker compose up -d

echo ""
echo "Waiting for Odoo to be ready..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:${ODOO_PORT:-8069}/web/login | grep -q "200"; then
        echo "[OK] Odoo is ready at http://localhost:${ODOO_PORT:-8069}"
        exit 0
    fi
    sleep 2
    printf "."
done

echo ""
echo "[WARN] Odoo did not respond within 60 seconds."
echo "       Check logs: docker compose logs odoo"
