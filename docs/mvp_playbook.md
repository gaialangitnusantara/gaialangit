# MVP Playbook: Duck Farming ERP
## Step-by-Step Guide for Claude Code Delivery

This document is the exact sequence of commands and actions to go from
zero to a working duck farming ERP. Each step has a clear input, action,
and verification. Do not skip steps.

---

## Prerequisites

- Docker Desktop installed and running
- Git installed
- Claude Code CLI installed (`npm install -g @anthropic-ai/claude-code`)
- Terminal access
- A browser for Odoo UI verification

---

## STEP 1: Initialize the Repository

```bash
# Create project directory
mkdir gaialangit-erp && cd gaialangit-erp
git init

# Copy the project structure (from the delivered package)
# This gives you: CLAUDE.md, .claude/, config/, scripts/, docs/, addons/

# Make scripts executable
chmod +x scripts/*.sh

# Create .env from template
cp .env.example .env
```

**Verify:** `ls -la` shows CLAUDE.md, docker-compose.yml, .env, scripts/, docs/, addons/, .claude/

---

## STEP 2: Smoke-Test Odoo Version

```bash
# Start only the database first
docker compose up -d db
sleep 5

# Test Odoo 18 (stable)
./scripts/smoke_test_version.sh odoo:18.0

# If you want to try Odoo 19 nightly:
# ./scripts/smoke_test_version.sh odoo:19.0
```

**Verify:** Script prints `[PASS]`.

**Action:** Edit `.env` and set `ODOO_IMAGE=odoo:18.0` (or whichever passed).

```bash
# Record the decision
echo "## Version Decision" >> docs/session_state.md
echo "Odoo version locked: $(grep ODOO_IMAGE .env)" >> docs/session_state.md
echo "Date: $(date)" >> docs/session_state.md
```

---

## STEP 3: Start the Stack

```bash
./scripts/start_odoo.sh
```

**Verify:** Open `http://localhost:8069` in browser. You see the Odoo database manager page.

---

## STEP 4: Initialize Database with Standard Modules

```bash
./scripts/init_db.sh
```

This installs: base, mail, stock, purchase, purchase_stock, sale_management,
account (with l10n_id), stock_account.

**Wait time:** 3-8 minutes on first run.

**Verify:**
1. Restart Odoo: `docker compose restart odoo` (wait 15 seconds)
2. Open `http://localhost:8069`
3. Login: admin / admin
4. You see the Odoo dashboard with Inventory, Purchase, Sales, Accounting apps

---

## STEP 5: Configure Company & Basics (Manual in Odoo UI)

Do these in the Odoo web interface:

### 5A. Company Setup
1. Settings → General Settings → Company
2. Set company name: **Gaialangit**
3. Set address (your farm address)
4. Save

### 5B. Warehouse
1. Inventory → Configuration → Warehouses
2. Verify "Main Warehouse" exists (created by default)
3. Note the stock location: WH/Stock

### 5C. Chart of Accounts
1. Accounting → Configuration → Chart of Accounts
2. Verify Indonesian chart (l10n_id) is loaded
3. Add 5 duck-specific accounts:

| Name | Code | Type |
|------|------|------|
| Biological WIP - Duck | 141300 | Current Assets |
| Inventory - Duck Eggs | 142310 | Current Assets |
| Inventory - Duck Meat | 142320 | Current Assets |
| Inventory - Duck Manure | 142330 | Current Assets |
| Abnormal Loss - Duck | 615300 | Expenses |

(Adjust codes to fit your l10n_id chart structure)

### 5D. Create Duck Products
1. Inventory → Products → Create

| Product Name | Type | Tracking | Category |
|---|---|---|---|
| Day-Old Duck (DOD) | Storable | By Lots | Raw Material |
| Duck Feed - Starter | Storable | By Lots | Raw Material |
| Duck Feed - Grower | Storable | By Lots | Raw Material |
| Duck Feed - Layer | Storable | By Lots | Raw Material |
| Duck Vaccine (Generic) | Storable | By Lots | Raw Material |
| Live Duck | Storable | By Lots | (set accounts to WIP) |
| Duck Egg | Storable | By Lots | Finished Goods |
| Duck Meat (Whole) | Storable | By Lots | Finished Goods |
| Duck Manure | Storable | By Lots | (set accounts to Byproduct) |

For each product, set:
- Product Type: Storable
- Tracking: By Lots
- Standard Price: estimated cost (can adjust later)
- Internal Reference: DOD-001, FEED-STR, etc.

### 5E. Create Stock Locations
1. Inventory → Configuration → Locations (enable Developer Mode first)
2. Create under WH:

| Location | Parent | Type |
|---|---|---|
| Duck Flock | WH | Internal |
| Finished Goods | WH/Stock | Internal |
| Byproduct | WH/Stock | Internal |

### 5F. Enable Developer Mode
1. Settings → Activate Developer Mode (at bottom of page)
2. This is needed for location configuration and later debugging

**Verify:** All products visible in Inventory → Products. All locations visible.

---

## STEP 6: Build agri_base_masterdata (First Custom Addon)

Open Claude Code in the project directory:

```bash
cd gaialangit-erp
claude
```

In Claude Code, say:

> Read CLAUDE.md and docs/session_state.md. Then read .claude/skills/odoo-module-scaffold/SKILL.md.
> Build the agri_base_masterdata addon with:
> - Models: agri.division, agri.site, agri.zone
> - Zone types: greenhouse, pond, duck_house, pen, processing
> - Security groups: group_farm_operator, group_shed_manager, group_finance_user, group_farm_admin
> - Top-level Farming menu with Configuration submenu
> - Full ir.model.access.csv for all groups and models
> Follow the scaffold skill exactly. Output structure A-F.

**After Claude Code generates the files:**

```bash
# Install the addon
./scripts/install_addon.sh agri_base_masterdata
```

**Verify:**
1. Restart Odoo: `docker compose restart odoo`
2. Login to Odoo
3. See "Farming" menu in top bar
4. Can create: Division → Site → Zone
5. Create test data:
   - Division: "Duck Farming"
   - Site: "Main Farm"
   - Zone: "Duck House A" (type: duck_house)
   - Zone: "Duck House B" (type: duck_house)

---

## STEP 7: Build agri_biological_batches (Batch Base Class)

In Claude Code:

> Read .claude/skills/odoo-module-scaffold/SKILL.md.
> Build agri_biological_batches addon with:
> - Depends on: agri_base_masterdata, stock
> - Model: agri.biological.batch (concrete, not abstract)
> - Fields: name, batch_type (selection), division_id, site_id, zone_id,
>   start_date, end_date, state (draft/active/harvesting/closed/cancelled),
>   initial_count, current_count (computed), last_gate_sync (Datetime),
>   odoo_stock_state (Text), company_id
> - State buttons on form: Start, Close, Cancel
> - Tree and form views under Farming → Operations → Batches
> Follow scaffold skill. Output structure A-F.

```bash
./scripts/install_addon.sh agri_biological_batches
```

**Verify:**
1. Restart Odoo
2. Farming → Operations → Batches
3. Can create a batch record, change state via buttons

---

## STEP 8: Build agri_duck_ops — Flock Batch Model (Phase 3A-1)

In Claude Code:

> Read .claude/skills/odoo-module-scaffold/SKILL.md and
> .claude/skills/odoo-lifecycle-gate/SKILL.md.
> Build agri_duck_ops addon. Start with the flock batch model only:
> - Depends on: agri_biological_batches, stock
> - Model: agri.flock.batch extending/inheriting batch behavior
> - Additional fields: batch_type selection (layer/broiler/breeder),
>   live_bird_product_id, lot_id, flock_location_id,
>   placement_date, current_head_count (computed from initial - mortality),
>   cumulative_mortality, cumulative_eggs
> - States: draft → placed → laying/finishing → harvesting → closed
> - Basic form with status bar, tree view
> - Menu under Farming → Duck Operations → Flock Batches
> Do NOT implement gate logic yet. Just the model and views.
> Output structure A-F.

```bash
./scripts/install_addon.sh agri_duck_ops
```

**Verify:** Can create a flock batch record in the UI.

---

## STEP 9: Implement Input Gate (Phase 3A-2)

In Claude Code:

> Read .claude/skills/odoo-lifecycle-gate/SKILL.md (Pattern 1: Input Gate).
> Add the input gate to agri_duck_ops:
> - action_place_flock() method on agri.flock.batch
> - Creates stock.move from receiving location to Duck Flock location
> - Updates state to 'placed', sets placement_date
> - Updates last_gate_sync
> - Add "Place Flock" button on form (visible in draft state only)
> Output structure A-F.

```bash
./scripts/upgrade_addon.sh agri_duck_ops
```

**Verify:**
1. Create a purchase order for 500 DOD
2. Receive the PO (goods receipt with lot assignment)
3. Create a flock batch, link the lot
4. Click "Place Flock"
5. Check Inventory → Products → Live Duck → stock at Duck Flock location shows 500

---

## STEP 10: Implement Feed Consumption Gate (Phase 3A-3)

In Claude Code:

> Read .claude/skills/odoo-lifecycle-gate/SKILL.md (Pattern 2: Consumption Gate).
> Add feed consumption to agri_duck_ops:
> - New model: agri.flock.feed.log (batch_id, date, product_id, quantity, uom_id,
>   state draft/confirmed, move_id, warehouse_location_id, consumption_location_id)
> - action_confirm_feed() creates stock.move reducing feed from warehouse
> - Feed log list embedded in flock batch form (One2many tab)
> Output structure A-F.

```bash
./scripts/upgrade_addon.sh agri_duck_ops
```

**Verify:**
1. Ensure feed products have stock (receive via purchase)
2. Open flock batch → Feed tab → Create feed log
3. Confirm feed log
4. Check feed product stock decreased by the logged quantity

---

## STEP 11: Implement Mortality Gate (Phase 3A-4) — CRITICAL

In Claude Code:

> Read .claude/skills/odoo-lifecycle-gate/SKILL.md (Pattern 3: Mortality Gate).
> This is the most critical gate. Add to agri_duck_ops:
> - New model: agri.flock.mortality (batch_id, date, quantity, cause selection
>   [disease/predator/heat_stress/unknown/other], notes, state draft/confirmed, move_id)
> - action_confirm_mortality() MUST in same transaction:
>   1. Validate quantity ≤ current_head_count
>   2. Create stock.move from flock location to scrap (with lot)
>   3. Confirm mortality record
>   4. Call batch._update_gate_sync()
> - current_head_count must be a computed field: initial - sum(confirmed mortality)
> - Mortality tab on flock batch form
> - Add _update_gate_sync() and _get_stock_snapshot() helpers to flock batch
> - Add "Reconciliation Check" button to flock batch form
> Output structure A-F.

```bash
./scripts/upgrade_addon.sh agri_duck_ops
```

**Verify (test all of these):**
1. Flock has 500 birds
2. Record mortality of 5 (cause: disease) → Confirm
3. `current_head_count` shows 495
4. Check stock: Live Duck at Duck Flock location = 495
5. Check stock: Scrap location shows 5
6. Click "Reconciliation Check" → should pass
7. Try to record mortality of 500 (> current count) → should fail with validation error

---

## STEP 12: Implement Egg Collection Gate (Phase 3A-5)

In Claude Code:

> Read .claude/skills/odoo-lifecycle-gate/SKILL.md (Pattern 4: Output Gate).
> Add egg collection to agri_duck_ops:
> - New model: agri.flock.egg.collection (batch_id, date, quantity, grade selection
>   [a/b/c/reject], notes, state draft/confirmed, move_id, lot_id, egg_product_id,
>   finished_goods_location_id)
> - action_confirm_egg_collection() creates lot and stock.move to finished goods
> - Lot name format: {batch_name}-EGG-{YYYYMMDD}
> - Egg Collection tab on flock batch form
> - cumulative_eggs computed field on batch
> Output structure A-F.

```bash
./scripts/upgrade_addon.sh agri_duck_ops
```

**Verify:**
1. Record egg collection: 250 eggs, grade A
2. Confirm → lot created, stock move done
3. Check Inventory → Products → Duck Egg → 250 in Finished Goods

---

## STEP 13: Implement Meat Harvest Gate (Phase 3A-6)

In Claude Code:

> Add end-of-cycle meat harvest to agri_duck_ops:
> - "Harvest" button on flock batch (visible in laying/finishing state)
> - Wizard or direct action: asks for harvest quantity, creates stock.move
>   for meat product to finished goods
> - After harvest: batch state → 'closed', end_date set
> - Remaining birds (current_head_count - harvest_qty) should be accounted for
>   (either all harvested or remaining recorded as final mortality)
> Output structure A-F.

```bash
./scripts/upgrade_addon.sh agri_duck_ops
```

**Verify:**
1. Set flock to finishing state
2. Click Harvest → enter quantity
3. Duck Meat appears in finished goods
4. Batch state = closed

---

## STEP 14: Implement Manure Capture Gate (Phase 3A-7)

In Claude Code:

> Read .claude/skills/odoo-lifecycle-gate/SKILL.md (Pattern 5: Byproduct Gate).
> Add manure capture to agri_duck_ops:
> - New model: agri.flock.manure.log (batch_id, date, estimated_kg, notes,
>   state draft/confirmed, move_id, lot_id)
> - action_confirm_manure() creates lot and stock.move to byproduct location
> - Manure tab on flock batch form
> Output structure A-F.

```bash
./scripts/upgrade_addon.sh agri_duck_ops
```

**Verify:**
1. Record manure: 50 kg
2. Confirm → lot created, stock move done
3. Duck Manure appears in Byproduct location

---

## STEP 15: Build Batch Cost Summary Report (Phase 3A-8)

In Claude Code:

> Add a read-only batch cost summary to agri_duck_ops:
> - New menu: Farming → Duck Operations → Cost Summary
> - Computed fields on flock batch:
>   - total_dod_cost (from purchase price × initial_head_count)
>   - total_feed_cost (sum of confirmed feed logs × product standard price)
>   - total_mortality_qty (sum of confirmed mortality)
>   - total_eggs_qty (sum of confirmed egg collections)
>   - total_manure_kg (sum of confirmed manure logs)
> - Tree view showing all batches with these summary columns
> - Form view with a "Cost Summary" tab showing breakdown
> This is for Finance to use when creating manual WIP journal entries.
> No journal creation logic. Read-only numbers only.
> Output structure A-F.

```bash
./scripts/upgrade_addon.sh agri_duck_ops
```

**Verify:** Open Cost Summary, see per-batch cost breakdown with correct totals.

---

## STEP 16: Full-Cycle Simulation (Phase 4)

This is a manual testing phase. No code changes.

### Simulate a Layer Flock (60 days):

1. **Day 0:** Purchase 500 DOD, receive into stock with lot
2. **Day 0:** Create flock batch, place flock (input gate)
3. **Day 1-7:** Record daily feed (starter feed, ~15kg/day)
4. **Day 3:** Record mortality: 3 birds (disease)
5. **Day 7:** Record mortality: 2 birds (unknown)
6. **Day 8-21:** Switch to grower feed, record daily (~25kg/day)
7. **Day 14:** Record mortality: 1 bird (heat_stress)
8. **Day 22-60:** Switch to layer feed, record daily (~30kg/day)
9. **Day 25+:** Record daily egg collection (start at 100, ramp to 350/day)
10. **Weekly:** Record manure capture (~100kg/week)
11. **Day 60:** Harvest remaining birds for meat
12. **Day 60:** Close flock batch

### After simulation:

1. Run Reconciliation Check → must PASS
2. Open Cost Summary → verify totals make sense
3. In Accounting → Journal Entries → Create manual WIP journal entry:
   - Dr: Biological WIP - Duck (total feed + DOD cost)
   - Cr: Clearing account
4. Create output transfer entry:
   - Dr: Inventory - Duck Eggs (estimated egg value)
   - Cr: Biological WIP - Duck
5. Verify the journal entries balance

### Document the month-end procedure:

Create `docs/month_end_procedure.md` with the exact steps Finance follows.

---

## STEP 17: Checkpoint — MVP Complete

If all of the following are true, the Duck Farming MVP is complete:

- [ ] Odoo starts reproducibly from `./scripts/start_odoo.sh`
- [ ] Standard modules installed with l10n_id
- [ ] agri_base_masterdata: Division → Site → Zone works
- [ ] agri_biological_batches: Base batch model works
- [ ] agri_duck_ops: All 7 gates create correct stock.move
- [ ] Input gate: DOD receipt → flock placement
- [ ] Feed gate: Daily consumption reduces stock
- [ ] Mortality gate: Same-transaction stock write-off
- [ ] Egg gate: Daily collection → finished goods
- [ ] Meat gate: End-of-cycle harvest → finished goods
- [ ] Manure gate: Periodic capture → byproduct
- [ ] Reconciliation check passes (flock count = stock count)
- [ ] Batch cost summary report is accurate
- [ ] Full 60-day flock cycle simulated end-to-end
- [ ] Manual month-end close documented and tested
- [ ] Security groups control access correctly
- [ ] All addons install/upgrade cleanly

**After MVP: refer to docs/roadmap.md for the next slice.**

---

## Claude Code Session Tips

### Starting a session
```bash
cd gaialangit-erp
claude
```
First message should always be:
> Read CLAUDE.md and docs/session_state.md. Then tell me what phase we're in and what the next step is.

### Keeping scope tight
If Claude Code tries to do too much:
> Stop. We're only working on [specific gate/model]. Don't touch anything else.

### After every coding session
Ask Claude Code to:
> Update docs/session_state.md with what we just completed and what's next.

### If an install fails
```bash
# Check what went wrong
docker compose logs odoo | tail -50

# Then tell Claude Code:
# "Install of agri_duck_ops failed. Here's the error: [paste error]"
```

### If you need to start fresh
```bash
docker compose down -v   # WARNING: destroys all data
./scripts/start_odoo.sh
./scripts/init_db.sh
./scripts/install_addon.sh agri_base_masterdata
./scripts/install_addon.sh agri_biological_batches
./scripts/install_addon.sh agri_duck_ops
```
