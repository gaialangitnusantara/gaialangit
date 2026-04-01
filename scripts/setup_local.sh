#!/bin/bash
# setup_local.sh — First-time local environment setup
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Gaialangit ERP — Local Setup ==="

# 1. Create .env from template if missing
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "[OK] Created .env from .env.example"
    echo "     Review and adjust values before proceeding."
else
    echo "[OK] .env already exists"
fi

# 2. Pull images
echo ""
echo "=== Pulling Docker images ==="
cd "$PROJECT_DIR"
docker compose pull

# 3. Create addon directory if missing
mkdir -p "$PROJECT_DIR/addons"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Review .env and adjust ODOO_IMAGE if needed"
echo "  2. Run: ./scripts/start_odoo.sh"
echo "  3. Run: ./scripts/init_db.sh"
