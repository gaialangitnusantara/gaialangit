# Session State

## Project
Gaialangit Integrated Farming ERP  
**Lead slice: Duck Farming**  
Target platform: Odoo 19 (with Odoo 18 fallback if unstable)  
Database: PostgreSQL 16  
Python target: 3.12

---

## Current phase
**Phase 4 — Financial Hardening Pause** ✅ COMPLETE (2026-04-02)  
Status: Full simulated flock cycle passed all checks. Manual close procedure documented.

### Phase 4 results
- **All addons installed:** `agri_base_masterdata`, `agri_biological_batches`, `agri_duck_ops` (76 modules)
- **Full flock simulation BATCH-SIM-2026-003:** ALL 12 STEPS PASS
  - Input gate (place_flock): PASS — move=done, 500 ducks moved WH→Flock
  - Feed gate: PASS — 150 kg consumed, feed_remaining=850 kg
  - Mortality gate: PASS — 5 ducks written off, count=495 matches stock=495
  - Egg collection: PASS — 2000 butir, lot auto-created, in WH/Stock
  - Harvest (consume + meat): PASS — 100 birds consumed, 75 kg meat, count=395 matches stock=395
  - Manure: PASS — 500 kg, lot auto-created, in WH/Stock
  - Reconciliation: PASS — batch=395 matches stock quant=395
  - Close: PASS — state=closed, end_date set

- **Cost summary verified:**
  - DOD cost: IDR 40,000,000 (500 birds × IDR 80,000 standard price)
  - Feed cost: IDR 1,230,000 (150 kg × IDR 8,200)
  - Mortality loss: IDR 400,000 (5 birds × IDR 80,000)
  - Eggs: 2,000 butir
  - Harvest: 100 birds, 75 kg meat

- **Manual month-end close procedure:** documented in `docs/month_end_close.md`

### Odoo 19 Discoveries (bugs fixed in agri_duck_ops)

| Finding | Fix Applied |
|---------|------------|
| `stock.move.line.picked` must be set AFTER `_action_assign()` — computed field `_compute_picked` resets it to False on state change | Added `move.move_line_ids.picked = True` between `_action_assign()` and `_action_done()` in all 6 gate models |
| `stock.location.scrap_location` boolean field removed in Odoo 19 | `_get_scrap_location()` changed to search `usage='inventory'` |
| `product.template.uom_po_id` removed in Odoo 19 | Removed from product creation (uses `uom_id` only) |
| `product.template.is_storable` must be explicitly set True for lot-tracked storable products | Must set `is_storable=True` separately after product creation |
| `uom.category` model removed in Odoo 19; UoMs have no categories | Use UoMs directly: create `Ekor` and `Butir` as standalone units |
| `agri.flock.egg.collection.grade` values must be lowercase (`'a'`, `'b'`, `'c'`, `'ungraded'`) | Fixed in simulation; code was correct |

### Known limitations accepted for Phase 4
1. Negative quants at Production virtual location (expected for production output moves)
2. `total_feed_cost` uses standard_price approximation — finance cross-checks with actual PO
3. No cost allocation engine — manual allocation of WIP to output products
4. No automatic WIP JE posting — all journal entries are manual

---

## Current phase
**Phase 3 — Duck Operations Slice** ✅ COMPLETE (2026-04-02)  
Status: Installed, validated via simulation, bugs fixed

### Phase 3 results (code complete, not yet validated)
- `agri_biological_batches` fix: added `data/sequences.xml` (ir.sequence for `agri.biological.batch`)
  - Prefix: `BATCH/YYYY/`, padding: 4
  - Added to manifest data list (before security, as required)
- `agri_duck_ops` addon scaffolded — 18 files:

#### 3A-1 Flock batch model
- `_inherit = 'agri.biological.batch'` (in-place extension, same model+table)
- `batch_type` overridden as Selection: layer / broiler / breeder
- `state` extended via `selection_add`: placed, laying, finishing
  - `ondelete` for each new state: `set draft` (safe module uninstall)
- Duck-specific fields: breed, live_bird_product_id, lot_id, flock_location_id,
  receiving_location_id, egg_product_id, meat_product_id, manure_product_id, placement_date
- Back-references: feed_log_ids, mortality_ids, egg_collection_ids, harvest_ids, manure_log_ids
- Computed (stored): cumulative_mortality, cumulative_eggs, harvest_count
- `current_count` overridden as stored computed (initial_count - mortality - harvest_count)
  - `create()` overridden to pop `current_count` from vals (prevent base model conflict)
- Cost fields (stored computed): total_feed_cost, total_dod_cost, total_mortality_loss
- Location helpers: `_get_production_location()`, `_get_scrap_location()`, `_get_finished_goods_location()`
- Anti-drift: `_update_gate_sync()`, `_get_stock_snapshot()`
- State transitions: action_place_flock, action_start_laying, action_start_finishing
  - Override action_start_harvesting: accepts placed/laying/finishing/active
  - Override action_close: accepts all duck active states

#### 3A-2 Input gate (action_place_flock)
- Validates: draft state, required fields, initial_count > 0
- stock.move: receiving_location → flock_location (qty=initial_count, lot=batch.lot_id)
- Full move chain: create → confirm → assign → done (same transaction)
- Sets state=placed, placement_date

#### 3A-3 Feed consumption gate (agri.flock.feed.log)
- Fields: batch_id, date, product_id, quantity, uom_id, lot_id, notes, state, move_id
- action_confirm(): warehouse.lot_stock_id → production virtual location
- Lot on move line if feed is lot-tracked

#### 3A-4 Mortality gate (agri.flock.mortality) — CRITICAL
- Fields: batch_id, date, quantity, cause (5 options), notes, state, move_id
- action_confirm(): flock_location → scrap (same transaction, anti-drift contract)
- Validates: qty > 0, qty <= current_count, live_bird_product set, flock_location set, lot set
- cumulative_mortality and current_count auto-recompute (stored computed, same transaction)

#### 3A-5 Egg output gate (agri.flock.egg.collection)
- Fields: batch_id, date, quantity, grade (4 options), notes, state, move_id, lot_id
- action_confirm(): generates lot {batch}-EGG-YYYYMMDD, production → finished goods
- cumulative_eggs auto-recomputes

#### 3A-6 Meat harvest gate (agri.flock.harvest)
- Fields: batch_id, date, harvest_count, meat_weight_kg, notes, state,
  move_consume_id, move_meat_id, lot_id
- action_confirm(): TWO stock.moves in same transaction:
  1. flock_location → production (consume live birds)
  2. production → finished goods (produce meat, lot: {batch}-MEAT-YYYYMMDD)
- harvest_count and current_count auto-recompute

#### 3A-7 Manure byproduct gate (agri.flock.manure.log)
- Fields: batch_id, date, estimated_kg, notes, state, move_id, lot_id
- action_confirm(): generates lot {batch}-MNR-YYYYMMDD, production → finished goods
- No routing to circular processing (deferred to Slice 4)

#### 3A-8 Batch cost summary report
- QWeb PDF report bound to agri.biological.batch
- Shows: head counts, DOD cost, feed cost (by line), mortality loss, egg/meat/manure output
- Finance note prominently shown: "No auto-posting. Use this to prepare manual WIP JEs."
- Uses standard_price as approximation; cross-reference PO lines for actuals

#### 3A-9 Reconciliation check
- action_reconciliation_check() on flock batch
- Compares: batch.current_count vs stock.quant live_bird qty in flock_location
- Raises ValidationError with discrepancy details on mismatch
- Updates gate sync markers on pass

#### Views and menus
- Standalone duck form/list views (priority=12, used by duck action only)
- Duck action: domain=[('batch_type', 'in', ('layer','broiler','breeder'))]
- Duck action explicitly bound to duck views via ir.actions.act_window.view
- Menus: Farming → Duck Operations → Flock Batches / Daily Operations (Feed, Eggs, Mortality, Manure) / Harvest
- Mortality confirmation has double-confirm dialog (UI guard)
- Harvest confirmation has double-confirm dialog (UI guard)

#### Security (ACL)
- 5 models × 4 groups = 20 access rows
- farm_operator: read+write+create (no unlink) on daily ops; read-only on harvest
- shed_manager: full CRUD on all gate models
- finance_user: read-only on all models
- farm_admin: full CRUD + unlink

---

## Current phase
**Phase 2 — Custom Addon Foundation** ✅ COMPLETE (2026-04-01)

### Phase 2 results
- `agri_base_masterdata` installed and verified (75 modules, no errors/warnings)
  - Division / Site / Zone models with hierarchy and constraints
  - 4 security groups using Odoo 19 `res.groups.privilege` pattern
  - Full ACL matrix (12 rows) per security_design.md
  - `res.users` extended with `site_id` (M2o) and `zone_ids` (M2m)
  - Farm Access tab on user form (admin-only)
  - Farming top-level menu + Configuration sub-menu
- `agri_biological_batches` installed and verified (75 modules, no errors/warnings)
  - `agri.biological.batch` with `mail.thread` + `mail.activity.mixin`
  - State machine: draft → active → harvesting → closed / cancelled
  - Anti-drift fields: `last_gate_sync`, `odoo_stock_state`
  - Record rules: operator=zone-scoped, shed_manager=site-scoped, admin=bypass
  - Gate method authorization check (`_check_gate_access`)
- Odoo 19 discovery: `category_id` removed from `res.groups` — must use `res.groups.privilege`
- Sequence `agri.biological.batch` must be created in data before `create()` works ← FIXED in this session

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

### 8. Flock batch inheritance strategy (Phase 3 decision)
Used `_inherit = 'agri.biological.batch'` without `_name` (in-place extension).
Duck-specific fields added to the same table. Acceptable for Slice 1.
When Slice 2 (hydroponic) begins, evaluate whether to refactor base as abstract
or add a separate `agri.crop.batch` model.

---

## Current addon plan — Slice 1 only

| Addon | Purpose | Status |
|-------|---------|--------|
| `agri_base_masterdata` | Division/Site/Zone hierarchy, security groups | ✅ Installed |
| `agri_biological_batches` | Generic biological batch base class | ✅ Installed (fix: sequences.xml added) |
| `agri_duck_ops` | Flock lifecycle, all gate postings, cost summary | ✅ Installed, validated via simulation (Phase 4) |

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
- None

---

## Next safest step
**Phase 4 is complete. Decide which slice to build next.**

Phase 4 exit criteria met:
- One full simulated flock cycle passed all checks ✅
- Manual month-end close documented and tested ✅
- All known issues fixed and/or accepted as known limitations ✅

### Candidate next steps (in priority order):
1. **UI smoke test** — test Phase 4 results manually in the Odoo web UI (verify menus, forms, report rendering)
2. **Security group UI test** — verify access control groups block/allow correctly per ACL matrix
3. **Decide Slice 2** — options: hydroponic crop operations, fish/aquaculture, or financial hardening with real data from actual duck cycle

**Previously:**

### Step-by-step validation (each gate must be tested)

**Pre-flight (in Odoo):**
1. Upgrade `agri_biological_batches` (adds sequences.xml):
   `./scripts/upgrade_addon.sh agri_biological_batches`
2. Install `agri_duck_ops`:
   `./scripts/install_addon.sh agri_duck_ops`
3. Verify 75+ modules loaded, no errors in logs

**Setup (one-time in Odoo UI):**
4. Create products from duck-specific products table above (all lot-tracked)
5. Confirm warehouse has a production virtual location (standard Odoo)
6. Create a "Duck Flock" internal location under WH/Stock for `flock_location_id`

**3A-2: Input gate**
7. Create purchase order for DOD (Live Duck product, with lot)
8. Validate purchase receipt → lot created in WH/Stock
9. Farming → Duck Operations → Flock Batches → New
10. Set: batch_type=layer, live_bird_product, lot, flock_location=Duck Flock, receiving_location=WH/Stock
11. Click "Place Flock" → verify stock.move created, state=placed, stock.quant at Duck Flock updated

**3A-3: Feed gate**
12. Duck Operations → Daily Operations → Feed Logs → New
13. Set batch, date, product=Duck Feed Layer, qty
14. Confirm → verify stock.move (WH/Stock → production), feed stock reduced

**3A-4: Mortality gate**
15. On flock batch form, Mortality tab → New row (qty=2, cause=unknown)
16. Confirm → verify stock.move (Duck Flock → Scrap), current_count decremented

**3A-5: Egg gate**
17. Egg Collections tab → New row (qty=50)
18. Confirm → verify stock.move (production → WH/Stock), egg lot auto-created

**3A-6: Harvest gate**
19. Start Harvesting on batch
20. Harvest tab → New row (harvest_count=100, meat_weight_kg=75)
21. Confirm → verify 2 stock.moves (bird consumption + meat output), current_count updated

**3A-7: Manure gate**
22. Manure tab → New row (estimated_kg=200)
23. Confirm → verify stock.move (production → WH/Stock), manure lot created

**3A-8: Cost summary report**
24. From flock batch form, print Batch Cost Summary → verify report renders with correct figures

**3A-9: Reconciliation check**
25. Click "Check Reconciliation" → should pass (stock.quant matches current_count)

**Close:**
26. Click "Close Batch" → verify state=closed, end_date set

---

## Slice 1 exit criteria checklist
- [x] Environment starts reproducibly from CLI
- [x] Standard modules installed with `l10n_id`
- [x] `agri_base_masterdata` installed — can create Division → Site → Zone
- [x] `agri_biological_batches` installed — base batch model available
- [x] `agri_duck_ops` installed — flock batch lifecycle works
- [x] Can receive DOD into stock and create flock batch
- [x] Can record feed consumption with stock reduction
- [x] Can record mortality with synchronized stock write-off
- [x] Can collect eggs into finished goods
- [x] Can harvest meat at end of cycle
- [x] Can capture manure into byproduct inventory
- [x] Can close flock batch
- [x] Reconciliation check passes (flock count = stock count)
- [x] Batch cost summary report is accurate
- [x] Manual WIP journal entry procedure is documented (`docs/month_end_close.md`)
- [x] Manual month-end close tested successfully (simulated, not with real data)
- [ ] All security groups control access correctly (not tested via UI — code is correct)
- [x] At least one full flock cycle simulated end-to-end (BATCH-SIM-2026-003)

---

## Notes for next session
- Start with Phase 0A (version smoke test)
- Do not scaffold addons until Phase 1 is complete
- Do not design WIP valuation, Coretax, or IoT
- Keep scope brutally narrow: duck farming only
