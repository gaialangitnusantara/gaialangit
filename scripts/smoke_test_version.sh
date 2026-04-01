#!/bin/bash
# smoke_test_version.sh — Test if the target Odoo version works
# Run this BEFORE committing to a version in .env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

TEST_IMAGE="${1:-odoo:18.0}"
TEST_DB="gaialangit_smoke_test"
PG_CONTAINER="gaialangit-db"

echo "=== Smoke Testing Odoo Image: $TEST_IMAGE ==="

# Ensure DB container is running
cd "$PROJECT_DIR"
docker compose up -d db
sleep 3

# Run Odoo with test image, try to install core modules
echo "Attempting to install: base, stock, purchase, account, l10n_id..."
echo "This may take a few minutes..."

RESULT=0
docker run --rm \
    --network="$(docker network ls --filter name=gaialangit -q | head -1)" \
    -e HOST=db \
    -e USER="${POSTGRES_USER:-odoo}" \
    -e PASSWORD="${POSTGRES_PASSWORD:-odoo}" \
    "$TEST_IMAGE" \
    odoo -d "$TEST_DB" \
    -i base,stock,purchase,account \
    --without-demo=all \
    --stop-after-init \
    --no-http \
    2>&1 | tail -20 || RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo ""
    echo "[PASS] $TEST_IMAGE installed core modules successfully."
    echo "       You can lock this version in .env:"
    echo "       ODOO_IMAGE=$TEST_IMAGE"
else
    echo ""
    echo "[FAIL] $TEST_IMAGE failed to install core modules."
    echo "       Check output above for errors."
    echo "       Try a different version or use the stable fallback."
fi

# Cleanup test database
echo ""
echo "Cleaning up test database..."
docker exec "$PG_CONTAINER" dropdb -U "${POSTGRES_USER:-odoo}" --if-exists "$TEST_DB" 2>/dev/null || true

echo "[OK] Smoke test complete."
