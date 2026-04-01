---
name: odoo-dev
description: "Use this skill for ANY Odoo environment or infrastructure task: starting/stopping Docker, initializing databases, installing or upgrading modules, running the Odoo CLI, debugging install failures, checking logs, managing the PostgreSQL container, or configuring odoo.conf. Also use when verifying module dependencies, checking if a standard Odoo external ID exists, or validating that a view xpath target is present. Trigger on mentions of 'odoo', 'docker compose', 'install module', 'upgrade addon', 'odoo.conf', 'init_db', 'odoo CLI', 'odoo-bin', or any infrastructure/DevOps task for this project."
---

# Odoo Development Environment Skill

## Quick Reference

| Task | Command |
|------|---------|
| First-time setup | `./scripts/setup_local.sh` |
| Start stack | `./scripts/start_odoo.sh` |
| Stop stack | `./scripts/stop_odoo.sh` |
| Create DB + install standard modules | `./scripts/init_db.sh` |
| Install custom addon | `./scripts/install_addon.sh <name>` |
| Upgrade custom addon | `./scripts/upgrade_addon.sh <name>` |
| Smoke-test Odoo version | `./scripts/smoke_test_version.sh odoo:18.0` |
| View Odoo logs | `docker compose logs -f odoo` |
| Odoo shell | `docker exec -it gaialangit-odoo odoo shell -d gaialangit --no-http` |
| PostgreSQL shell | `docker exec -it gaialangit-db psql -U odoo -d gaialangit` |

## Environment Architecture

```
docker-compose.yml
├── odoo service (image pinned in .env)
│   ├── config/odoo.conf (mounted read-only)
│   └── addons/ (mounted as /mnt/extra-addons)
└── db service (postgres:16-alpine)
```

## Version Lock Process

Before any development:
1. Run `./scripts/smoke_test_version.sh odoo:19.0` (or target version)
2. If PASS → set `ODOO_IMAGE=odoo:19.0` in `.env`
3. If FAIL → try `./scripts/smoke_test_version.sh odoo:18.0`
4. Document decision in `docs/session_state.md`
5. Never change version mid-development without full retest

## Standard Module Install Order

The `init_db.sh` script installs these in one pass:
```
base, mail, stock, purchase, purchase_stock,
sale_management, account, stock_account, l10n_id
```

Deferred modules (install only when their slice begins):
- `mrp` — production orders (Slice 2+)
- `quality` — QC workflows
- `account_accountant` — advanced accounting
- `analytic` — cost center tracking
- `account_asset` — fixed assets
- `maintenance` — equipment maintenance
- `website_sale` — e-commerce

To install a deferred module:
```bash
docker exec -u odoo gaialangit-odoo \
  odoo -d gaialangit -i <module_name> --stop-after-init --no-http
```

## Custom Addon Install Order

Always install in dependency order:
1. `agri_base_masterdata` (no custom dependencies)
2. `agri_biological_batches` (depends on agri_base_masterdata)
3. `agri_duck_ops` (depends on agri_biological_batches)

If install fails:
1. Check logs: `docker compose logs odoo | tail -50`
2. Common issues:
   - Missing dependency in `__manifest__.py`
   - Invalid XML ID reference
   - Python import error
   - `ir.model.access.csv` referencing nonexistent group
3. Fix the issue, then retry install (no need to restart stack)

## Validating XML Inheritance

Before writing ANY xpath in a view XML file:

```bash
# 1. Find the external ID of the view you want to inherit
docker exec -it gaialangit-odoo odoo shell -d gaialangit --no-http <<'EOF'
view = env['ir.ui.view'].search([('name', 'ilike', 'stock.picking.form')])
for v in view:
    print(f"ID: {v.id}, XML_ID: {v.xml_id}, Name: {v.name}")
EOF

# 2. Check the view's arch for your xpath target
docker exec -it gaialangit-odoo odoo shell -d gaialangit --no-http <<'EOF'
view = env.ref('stock.view_picking_form')
print(view.arch)
EOF
```

If the external ID doesn't exist or the xpath target is missing: STOP.
Report it as a blocker. Do not guess.

## Checking Odoo Logs for Errors

```bash
# Full logs
docker compose logs odoo

# Follow live
docker compose logs -f odoo

# Filter for errors
docker compose logs odoo 2>&1 | grep -i "error\|traceback\|warning"

# Last 100 lines
docker compose logs --tail=100 odoo
```

## Database Operations

```bash
# List databases
docker exec gaialangit-db psql -U odoo -l

# Drop and recreate (DESTRUCTIVE)
docker exec gaialangit-db dropdb -U odoo gaialangit
./scripts/init_db.sh

# Backup
docker exec gaialangit-db pg_dump -U odoo gaialangit > backup.sql

# Restore
cat backup.sql | docker exec -i gaialangit-db psql -U odoo gaialangit
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "database does not exist" | Run `./scripts/init_db.sh` |
| "module not found" | Check addon is in `addons/` and has `__manifest__.py` |
| Port conflict on 8069 | Change `ODOO_PORT` in `.env` |
| Port conflict on 5432 | Change `PG_PORT` in `.env` |
| Container won't start | `docker compose down -v` then restart (WARNING: destroys data) |
| Odoo shows old code | Restart: `docker compose restart odoo` |
| Need to update addons list | In Odoo UI: Settings → Activate developer mode → Apps → Update Apps List |

## For More Details

Read `references/odoo_cli_reference.md` for full Odoo CLI flag documentation.
