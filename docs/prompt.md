# prompt.md

You are building the Gaialangit Integrated Farming ERP from zero inside this repo.

Read first:
1. CLAUDE.md
2. docs/session_state.md
3. PRD.md

Then follow this exact strategy.

---

## PHASE 0 — ENVIRONMENT BOOTSTRAP

### 0A. Version lock
1. Pull Odoo 19 nightly Docker image
2. Create empty test database
3. Install `stock`, `purchase`, `account` with `l10n_id`
4. If any install fails or views break, fall back to Odoo 18 Community
5. Record the exact pinned image tag in `.env`
6. Document the decision in `docs/session_state.md`

### 0B. Infrastructure files
Create or validate:
- `docker-compose.yml` (Odoo + PostgreSQL 16, pinned versions)
- `config/odoo.conf` (with `addons` mount path)
- `scripts/setup_local.sh`
- `scripts/start_odoo.sh`
- `scripts/stop_odoo.sh`
- `scripts/init_db.sh`
- `scripts/install_addon.sh`
- `scripts/upgrade_addon.sh`
- `.env.example` (with version pin slot)
- `.gitignore`
- `README.md`

### 0C. Validation
- Odoo starts and shows login page
- Empty DB can be created via CLI
- `addons/` directory is mounted and visible to Odoo
- Scripts are executable and documented

**Do not create any business logic in this phase.**

---

## PHASE 1 — STANDARD ODOO FOUNDATION + SECURITY DESIGN

### 1A. Install standard modules
```
stock, purchase, purchase_stock, sale_management,
account (with l10n_id), stock_account, mail
```

### 1B. Baseline configuration
Document (do not automate yet) the following setup assumptions:
- Company: Gaialangit
- Warehouse: Main warehouse with appropriate locations
- Chart of accounts: `l10n_id` standard + 5 duck-specific accounts
- Journals: Sales, Purchase, Stock, Miscellaneous (for manual WIP JEs)
- Taxes: Standard Indonesian VAT via `l10n_id`
- Products to create: DOD/pullet, duck feed, duck vaccine, live duck, duck egg, duck meat, duck manure

### 1C. Security groups design
Define (in a design doc, not code yet) four groups:
- `group_farm_operator` — daily data entry
- `group_shed_manager` — batch management
- `group_finance_user` — journal entries, reports
- `group_farm_admin` — configuration

Map each group to the models they will access and the CRUD permissions.

**Do not build custom addons in this phase.**

---

## PHASE 2 — CUSTOM ADDON FOUNDATION

Build in this order. Each addon must be installable before proceeding to the next.

### 2A. `agri_base_masterdata`
Purpose: Physical hierarchy and security groups.

Must include:
- `__init__.py`, `__manifest__.py`
- `models/division.py` — name, code, active
- `models/site.py` — name, division_id, address fields
- `models/zone.py` — name, site_id, zone_type (greenhouse/pond/duck_house/pen/processing)
- `security/security.xml` — four groups defined above
- `security/ir.model.access.csv` — CRUD per group per model
- `views/division_views.xml` — form + tree + action
- `views/site_views.xml` — form + tree + action
- `views/zone_views.xml` — form + tree + action
- `views/menus.xml` — top-level Farming menu + sub-menus

Validation: Install succeeds. Can create Division → Site → Zone in UI.

### 2B. `agri_biological_batches`
Purpose: Generic biological batch base class.

Must include:
- `models/biological_batch.py` — abstract or concrete base with:
  - name, batch_type, division_id, site_id, zone_id
  - start_date, end_date, state
  - initial_count, current_count (computed)
  - last_gate_sync, odoo_stock_state (Char/Text for JSON)
  - state machine: draft → active → harvesting → closed / cancelled
- `security/ir.model.access.csv`
- `views/` — base form/tree (may be inherited by division-specific addons)

Validation: Install succeeds. Base batch model is available.

---

## PHASE 3 — DUCK OPERATIONS SLICE

### 3A. `agri_duck_ops`
Purpose: Complete flock lifecycle with all gate postings.

**Build incrementally in this sub-order:**

#### 3A-1. Flock batch model
- Inherit or extend `agri.biological.batch` for duck-specific fields
- `batch_type` selection: layer / broiler / breeder
- Duck house/pen zone linkage
- Flock-specific states: draft → placed → laying/finishing → harvesting → closed

#### 3A-2. Input gate — DOD/pullet receipt
- Receive purchased DODs into standard stock (via purchase receipt)
- Create flock batch and link to received lot
- Transfer stock from receiving location to flock's virtual/internal location
- Update batch `initial_head_count`

#### 3A-3. Consumption gate — feed
- `agri.flock.feed.log` model: batch_id, date, product_id, quantity, lot_id
- On confirm: create `stock.move` reducing feed from warehouse
- Feed cost accumulated on batch for reporting

#### 3A-4. Mortality gate
- `agri.flock.mortality` model: batch_id, date, quantity, cause, notes
- On confirm: create stock write-off `stock.move` (live bird → scrap)
- **Same database transaction** — if stock move fails, mortality record rolls back
- Recompute `current_head_count`
- Update `last_gate_sync`

#### 3A-5. Output gate — eggs
- `agri.flock.egg.collection` model: batch_id, date, quantity, grade, notes
- On confirm: create `stock.move` receiving eggs into finished goods
- Generate lot from batch reference + date

#### 3A-6. Output gate — meat harvest
- End-of-cycle workflow
- Record harvest quantity and create `stock.move` to finished goods
- Close flock batch

#### 3A-7. Byproduct gate — manure
- `agri.flock.manure.log` model: batch_id, date, estimated_kg, notes
- On confirm: create `stock.move` receiving manure into byproduct location
- Lot-tracked for future circular economy linkage

#### 3A-8. Batch cost summary report
- Read-only report showing per-batch:
  - Total feed cost
  - Total DOD/pullet cost
  - Total vaccine/supplement cost
  - Mortality loss quantity
  - Output quantities (eggs, meat)
  - Manure captured
- This report supports Finance for manual WIP journal entries
- No auto-posting. No journal creation.

#### 3A-9. Reconciliation check
- Action/report comparing:
  - Flock batch `current_head_count` vs Odoo `stock.quant` for live bird product
  - Cumulative egg collections vs Odoo egg product stock moves
  - Cumulative feed consumption vs Odoo feed stock moves
- Flag any discrepancy

Validation for each sub-step: addon upgrades cleanly, gate creates correct stock.move, UI works.

---

## PHASE 4 — FINANCIAL HARDENING PAUSE

Do not build new addons. Instead:
1. Run a simulated full flock cycle end-to-end in the test environment
2. Verify all stock moves are correct
3. Verify reconciliation check passes
4. Finance prepares manual WIP journal entries using batch cost summary
5. Document the manual month-end close procedure
6. Identify any missing fields, broken flows, or UX issues
7. Fix issues found
8. Update session_state.md with lessons learned

**Exit criteria:**
- One full simulated flock cycle passes all checks
- Manual month-end close is documented and tested
- All known issues are logged and either fixed or accepted as known limitations

**Only after Phase 4 passes: decide which slice to build next.**

---

## SUBSEQUENT PHASES (not started until Phase 4 complete)

### PHASE 5 — Second vertical slice
Choose based on business priority: Hydroponic Melon or Aquaculture.
Repeat the pattern: scaffold → gates → reconciliation → financial hardening pause.

### PHASE 6 — Circular economy
Build `agri_circular_economy` to route duck manure (already in inventory) into compost/vermiculture.

### PHASE 7 — Procurement & finance extensions
Build `agri_procurement_extension` and `agri_finance_extension` when volume justifies.
Consider `agri_wip_valuation` only if manual closes are proven painful after 3+ cycles.

### PHASE 8 — IoT
Build `agri_iot_base` and monitoring modules when sensor hardware is deployed.

### PHASE 9 — Compliance & reporting
Build Coretax connector, KPI dashboard, sustainability reporting, traceability portal.

---

## GLOBAL RULES
- One pinned Odoo version (19 or 18 fallback)
- Biological WIP remains outside continuous discrete stock truth
- Standard Odoo is official ledger at lifecycle gates
- No XML inheritance without verified external ID and xpath
- One bounded task at a time
- Update docs/session_state.md after every meaningful step
- If scope is too large, stop and split it
- Never say "done" without specific validation steps completed
- **After every gate implementation, verify stock impact in Odoo UI manually**

## OUTPUT FORMAT FOR EACH RESPONSE
A. Scope summary  
B. Files to modify  
C. Implementation  
D. Validation (specific test steps, not generic "verify it works")  
E. Session-state update  
F. Next safest step  

---

Begin now with PHASE 0 only.
Do not skip ahead.
