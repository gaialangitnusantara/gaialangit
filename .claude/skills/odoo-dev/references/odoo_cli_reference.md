# Odoo CLI Reference

## Core Commands

### Initialize / Install modules
```bash
odoo -d <dbname> -i <module1,module2> --stop-after-init --no-http
```
- `-d` — target database name
- `-i` — comma-separated list of modules to install
- `--stop-after-init` — exit after install completes (don't start web server)
- `--no-http` — don't bind HTTP port (avoids conflicts when main instance is running)
- `--without-demo=all` — skip demo data

### Upgrade modules
```bash
odoo -d <dbname> -u <module1,module2> --stop-after-init --no-http
```
- `-u` — comma-separated list of modules to upgrade

### Interactive shell
```bash
odoo shell -d <dbname> --no-http
```
Opens a Python REPL with access to `env` (Odoo environment).
Useful for:
- Querying models: `env['stock.move'].search_count([])`
- Checking views: `env.ref('stock.view_picking_form').arch`
- Verifying data: `env['product.product'].search([('name', 'ilike', 'duck')])`

### Scaffold a new module
```bash
odoo scaffold <module_name> <target_directory>
```
Creates a skeleton addon. However, for this project we use our own
scaffold skill (`.claude/skills/odoo-module-scaffold/`) which produces
a more complete structure.

## Common Flags

| Flag | Purpose |
|------|---------|
| `-d <dbname>` | Target database |
| `-i <modules>` | Install modules (comma-separated) |
| `-u <modules>` | Upgrade modules (comma-separated) |
| `-c <path>` | Config file path |
| `--addons-path=<paths>` | Comma-separated addon directories |
| `--stop-after-init` | Exit after init (don't serve) |
| `--no-http` | Don't start HTTP server |
| `--without-demo=all` | No demo data |
| `--log-level=debug` | Verbose logging |
| `--dev=xml` | Auto-reload XML on save (dev mode) |
| `--dev=all` | Auto-reload Python + XML (dev mode) |

## Running Inside Docker

All commands must be prefixed with `docker exec`:

```bash
# Install
docker exec -u odoo gaialangit-odoo \
  odoo -d gaialangit -i <module> --stop-after-init --no-http

# Upgrade
docker exec -u odoo gaialangit-odoo \
  odoo -d gaialangit -u <module> --stop-after-init --no-http

# Shell
docker exec -it gaialangit-odoo \
  odoo shell -d gaialangit --no-http

# Check module is loadable (dry run)
docker exec -u odoo gaialangit-odoo \
  python3 -c "import importlib; importlib.import_module('odoo.addons.<module_name>')"
```

## Module Dependency Resolution

When installing module A that depends on B:
- If B is not installed, Odoo auto-installs B first
- If B fails, A also fails
- Always verify `__manifest__.py` `depends` list matches what's available

To check what's installed:
```bash
docker exec -it gaialangit-odoo odoo shell -d gaialangit --no-http <<'EOF'
installed = env['ir.module.module'].search([('state', '=', 'installed')])
for m in installed.sorted('name'):
    print(m.name)
EOF
```

## Update Apps List

After adding a new addon to `addons/`, Odoo needs to discover it:

Option 1 — CLI:
```bash
docker exec -u odoo gaialangit-odoo \
  odoo -d gaialangit --stop-after-init --no-http -u base
```

Option 2 — UI:
1. Enable Developer Mode (Settings → Activate developer mode)
2. Apps → Update Apps List → Update

Option 3 — Shell:
```bash
docker exec -it gaialangit-odoo odoo shell -d gaialangit --no-http <<'EOF'
env['ir.module.module'].update_list()
env.cr.commit()
EOF
```
