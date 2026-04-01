# CLAUDE.md

## Project
Gaialangit Integrated Farming ERP on Odoo
**Lead slice: Duck Farming**

## Read first
Before any task, read in this order:
1. This file (CLAUDE.md)
2. docs/session_state.md
3. docs/prd.md
4. docs/roadmap.md (if planning next step)
5. Relevant addon files under addons/

## Skills
This project includes custom Claude Code skills in `.claude/skills/`.
Read the relevant SKILL.md before performing any of these tasks:
- **odoo-dev**: Environment setup, Odoo CLI, Docker, module install/upgrade
- **odoo-module-scaffold**: Creating new Odoo addon modules
- **odoo-lifecycle-gate**: Implementing biological lifecycle gate postings with stock sync

## Odoo version policy
- Primary target: Odoo 19 (if nightly ORM is stable)
- Fallback: Odoo 18 Community (if Odoo 19 has breaking issues)
- Version is locked in `.env` after Phase 0 smoke test
- Never mix versions. All work targets one pinned image tag.

## Global technical constraints
- Python: 3.12
- PostgreSQL: 16
- Standard Odoo = transactional source of truth
- Custom addons extend, never replace, Odoo core
- No speculative fields — every field must have a known consumer
- No unverified XML inheritance
- No task is complete without validation

## Biological WIP rule
Biological growth is NOT tracked as continuous live stock in standard Odoo.
Custom operational models hold truth during active lifecycle.
Standard stock/MRP postings happen ONLY at lifecycle gates.

Anti-drift rule: Every gate posting updates BOTH the biological model AND
Odoo stock in the SAME database transaction. If one fails, both roll back.

## Accounting rule — manual first
No automated WIP valuation engine until:
1. At least one division has 3+ full production cycles with real data
2. Manual journal entries used for 2+ month-end closes
3. Finance validates CoA mapping against actual transactions

## CoA rule — minimal and incremental
Start with `l10n_id` standard chart. Add only accounts for the current slice.
Duck slice: 5 accounts (WIP, FG-Eggs, FG-Meat, Byproduct-Manure, Abnormal Loss).

## Security groups (must exist before any addon)
- `group_farm_operator` — daily data entry
- `group_shed_manager` — batch lifecycle management
- `group_finance_user` — journal entries, reports
- `group_farm_admin` — full configuration

## XML inheritance rule
Before inheriting any standard Odoo view:
1. Verify external ID exists in pinned Odoo version
2. Verify parent view renders
3. Verify xpath target element is present
4. If any check fails → STOP and report blocker
5. Document verified external ID in a code comment

## Working style
- One bounded task at a time
- One addon at a time
- If task is too large → split before starting
- After every gate implementation → verify stock impact in Odoo UI
- Always update docs/session_state.md before ending

## Output structure for every response
A. Scope summary
B. Files to modify
C. Implementation
D. Validation (specific test steps)
E. Session-state update
F. Next safest step

## Validation rules
For any addon work, validate:
- `__manifest__.py` syntax and dependency list
- Python imports resolve
- XML IDs are unique and reference valid models
- `ir.model.access.csv` references existing groups
- Menu → action → view chain is coherent
- Install/upgrade succeeds: `./scripts/install_addon.sh <name>`

## Build order (duck-first)
1. Environment bootstrap + version lock
2. Standard module install (with `l10n_id`)
3. `agri_base_masterdata`
4. `agri_biological_batches`
5. `agri_duck_ops`
6. Financial hardening pause (manual JEs, reconciliation)
7. Second slice (decided after duck validation)
8. Subsequent slices per docs/roadmap.md
