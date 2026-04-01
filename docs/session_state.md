# Session State

## Project
Gaialangit Integrated Farming ERP  
**Lead slice: Duck Farming**  
Target platform: Odoo 19 (with Odoo 18 fallback if unstable)  
Database: PostgreSQL 16  
Python target: 3.12

---

## Current phase
**Phase 1 — Standard Odoo Foundation + Security Design** ✅ COMPLETE (2026-04-01)

### Phase 1 results
- `docs/baseline_config.md` — company, warehouse, CoA, journals, taxes, 10 products, 6 categories, UoMs, location design
- `docs/security_design.md` — 4 groups, model access matrix, menu visibility, record rules, Odoo group mappings, implementation notes
- 4 open questions documented for business confirmation before coding
- Standard modules already installed (Phase 0)

### Phase 0 results
- **Odoo version locked: `odoo:19.0`**
- Image digest: `odoo@sha256:19b1d3cc053b31f418b3db1f57c709c0e589a9c29fdabdff966b60d05d757028`
- Smoke test (2026-04-01): `base,stock,purchase,account,l10n_id` → 62 modules, no errors
- DB init: `gaialangit` database created with 73 modules (full Slice 1 standard set)
- Login page returns HTTP 200 ✅
- All scripts executable, `.env` created and locked

---

## Accepted architecture decisions

### 1. Duck-first vertical slice
The project starts with duck farming as the proving ground.
All architectural patterns (biological batch, lifecycle gates, stock sync, financial close)
are validated on duck operations before extending to other divisions.

### 2. Biological WIP rule
During active biological growth, operational truth lives in custom biological models.
Standard Odoo stock/MRP postings happen only at lifecycle gates.

**Anti-drift enforcement:** Every gate posting updates both the biological model and
standard Odoo stock in the same database transaction. A reconciliation check is available
to compare the two at any time.

### 3. Manual-first accounting
No automated WIP valuation engine in Slice 1.
Finance posts WIP journal entries manually using batch cost summary reports.
Automated valuation is considered only after 3+ production cycles with manual closes.

### 4. Minimal CoA
Start with `l10n_id` standard chart. Add only 5 accounts for duck operations.
Grow the chart incrementally with each new slice.

### 5. Deferred complexity
The following are explicitly deferred and not designed in detail until needed:
- WIP valuation engine / subledger
- Coretax connector
- IoT integration
- Circular economy routing
- Advanced procurement (RFI/RFQ/comparison)
- Transfer pricing for internal byproducts

### 6. Odoo version policy
Pin one version. Smoke-test Odoo 19 nightly; fall back to Odoo 18 if ORM or views break.
Document pinned image tag in `.env`.

### 7. Security groups
Four groups defined before any addon scaffolding:
- `group_farm_operator`
- `group_shed_manager`
- `group_finance_user`
- `group_farm_admin`

---

## Current addon plan — Slice 1 only

| Addon | Purpose | Status |
|-------|---------|--------|
| `agri_base_masterdata` | Division/Site/Zone hierarchy, security groups | Not started |
| `agri_biological_batches` | Generic biological batch base class | Not started |
| `agri_duck_ops` | Flock lifecycle, all gate postings, cost summary | Not started |

All other addons from the full PRD are deferred until Slice 1 is validated.

---

## Standard Odoo modules — Slice 1

| Module | Purpose | Status |
|--------|---------|--------|
| `stock` | Inventory management | ✅ Installed |
| `purchase` | Purchase orders | ✅ Installed |
| `purchase_stock` | Purchase → stock integration | ✅ Installed |
| `sale_management` | Sales orders | ✅ Installed |
| `account` + `l10n_id` | Accounting with Indonesian chart | ✅ Installed |
| `stock_account` | Inventory valuation | ✅ Installed |
| `mail` | Messaging / chatter | ✅ Installed |

---

## Duck-specific products to create

| Product | Type | Tracking | Category |
|---------|------|----------|----------|
| Day-Old Duck (DOD) | Storable | Lot | Raw Material |
| Duck Pullet | Storable | Lot | Raw Material |
| Duck Feed — Starter | Storable | Lot | Raw Material |
| Duck Feed — Grower | Storable | Lot | Raw Material |
| Duck Feed — Layer | Storable | Lot | Raw Material |
| Duck Vaccine (generic) | Storable | Lot | Raw Material |
| Live Duck | Storable | Lot | WIP |
| Duck Egg | Storable | Lot | Finished Good |
| Duck Meat (whole) | Storable | Lot | Finished Good |
| Duck Manure | Storable | Lot | Byproduct |

---

## Duck-specific CoA additions

| Code | Name | Type |
|------|------|------|
| TBD | Biological WIP — Duck | Balance Sheet (Current Asset) |
| TBD | Inventory — Duck Eggs | Balance Sheet (Current Asset) |
| TBD | Inventory — Duck Meat | Balance Sheet (Current Asset) |
| TBD | Inventory — Duck Manure | Balance Sheet (Current Asset) |
| TBD | Abnormal Loss — Duck | P&L (Expense) |

Account codes will be assigned after `l10n_id` chart is installed and reviewed.

---

## Current blockers
- None for Phase 0 — environment is ready

---

## Next safest step
**Phase 2: Scaffold and install `agri_base_masterdata`**
All pre-conditions met — security design locked, no open questions.

1. Scaffold addon using `odoo-module-scaffold` skill
2. Division → Site → Zone hierarchy models
3. Security groups + ACL + record rules (per `docs/security_design.md`)
4. `./scripts/install_addon.sh agri_base_masterdata`
5. Validate: create Division → Site → Zone; confirm group ACL blocks unauthorized access

Key implementation notes (from locked decisions):
- `site_id` Many2one (not M2M) on `res.users`
- `shed_manager` gets `purchase.group_purchase_user`
- Gate methods check `group_shed_manager` (farm_admin inherits via `implied_ids`)
- finance_user has no record rule restrictions

---

## Slice 1 exit criteria checklist
- [ ] Environment starts reproducibly from CLI
- [ ] Standard modules installed with `l10n_id`
- [ ] `agri_base_masterdata` installed — can create Division → Site → Zone
- [ ] `agri_biological_batches` installed — base batch model available
- [ ] `agri_duck_ops` installed — flock batch lifecycle works
- [ ] Can receive DOD into stock and create flock batch
- [ ] Can record feed consumption with stock reduction
- [ ] Can record mortality with synchronized stock write-off
- [ ] Can collect eggs into finished goods
- [ ] Can harvest meat at end of cycle
- [ ] Can capture manure into byproduct inventory
- [ ] Can close flock batch
- [ ] Reconciliation check passes (flock count = stock count)
- [ ] Batch cost summary report is accurate
- [ ] Manual WIP journal entry procedure is documented
- [ ] Manual month-end close tested successfully
- [ ] All security groups control access correctly
- [ ] At least one full flock cycle simulated end-to-end

---

## Notes for next session
- Start with Phase 0A (version smoke test)
- Do not scaffold addons until Phase 1 is complete
- Do not design WIP valuation, Coretax, or IoT
- Keep scope brutally narrow: duck farming only
