# Gaialangit Integrated Farming ERP

Odoo-based ERP for multi-sector integrated farming: duck farming, hydroponics, aquaculture, and circular economy processing.

## Current Status: Slice 1 — Duck Farming MVP

## Quick Start

```bash
# 1. Setup
cp .env.example .env
chmod +x scripts/*.sh
./scripts/setup_local.sh

# 2. Start
./scripts/start_odoo.sh

# 3. Initialize database
./scripts/init_db.sh

# 4. Install custom addons (in order)
./scripts/install_addon.sh agri_base_masterdata
./scripts/install_addon.sh agri_biological_batches
./scripts/install_addon.sh agri_duck_ops

# 5. Open http://localhost:8069 (admin/admin)
```

## Project Structure

```
gaialangit-erp/
├── CLAUDE.md                    # Claude Code instructions
├── docker-compose.yml           # Odoo + PostgreSQL stack
├── .env.example                 # Environment template
├── config/
│   └── odoo.conf                # Odoo configuration
├── scripts/
│   ├── setup_local.sh           # First-time setup
│   ├── start_odoo.sh            # Start stack
│   ├── stop_odoo.sh             # Stop stack
│   ├── init_db.sh               # Create DB + install standard modules
│   ├── install_addon.sh         # Install custom addon
│   ├── upgrade_addon.sh         # Upgrade custom addon
│   └── smoke_test_version.sh    # Test Odoo version compatibility
├── addons/                      # Custom Odoo addons
│   ├── agri_base_masterdata/    # Division/Site/Zone + security groups
│   ├── agri_biological_batches/ # Generic biological batch base
│   └── agri_duck_ops/           # Duck flock lifecycle + gates
├── docs/
│   ├── prd.md                   # Product requirements
│   ├── roadmap.md               # Scaling roadmap (12 milestones)
│   ├── session_state.md         # Current build state
│   ├── prompt.md                # Claude Code phase instructions
│   ├── mvp_playbook.md          # Step-by-step MVP delivery guide
│   ├── business_process_diagram.md
│   └── business_process_diagram_wip_reference.md
└── .claude/
    └── skills/                  # Claude Code custom skills
        ├── odoo-dev/            # Environment, CLI, Docker
        ├── odoo-module-scaffold/# Addon creation patterns
        └── odoo-lifecycle-gate/ # Biological gate + stock sync
```

## Documentation

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Engineering rules for Claude Code |
| `docs/mvp_playbook.md` | Step-by-step MVP delivery (start here) |
| `docs/prd.md` | Product requirements (duck-first) |
| `docs/roadmap.md` | Full scaling plan (12 milestones) |
| `docs/session_state.md` | Current progress tracker |

## Technology Stack

- **Odoo:** 18.0 (or 19.0 if stable — see .env)
- **PostgreSQL:** 16
- **Python:** 3.12
- **Deployment:** Docker Compose

## License

Proprietary — Gaialangit
