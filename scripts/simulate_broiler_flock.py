"""
simulate_broiler_flock.py
=========================
45-day broiler flock cycle simulation for Gaialangit ERP.

Run via Odoo shell:
  docker exec -i gaialangit-odoo odoo shell -d gaialangit --no-http \\
    < scripts/simulate_broiler_flock.py

Key differences from layer simulation:
  - batch_type = 'broiler'
  - 300 DOD at Rp 12,000
  - Feed: Starter (days 1-10) / Grower (days 11-25) / Grower-as-Finisher (days 26-45)
  - No egg collection
  - Manure every 7 days at 60 kg
  - Day 45: harvest ALL remaining birds → Duck Meat → close batch

State path: draft → placed → finishing → harvesting → harvest gate → closed

Odoo 19 notes (same as layer script):
  - is_storable=True after product creation
  - No uom_po_id, no uom.category
  - picked=True after _action_assign()
  - Feed / Vaccine: tracking='none' (bulk material)
"""

from datetime import date, timedelta

print()
print("=" * 65)
print("  Gaialangit — Broiler Flock 45-Day Simulation")
print("=" * 65)

FLOCK_START     = date(2026, 4, 10)   # Simulation day 1
LOT_NAME        = 'DOD-BROILER-SIM-2026-001'
MEAT_KG_PER_BIRD = 1.8                # Estimated meat yield per harvested bird

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def sim_date(day):
    return FLOCK_START + timedelta(days=day - 1)

def ok(msg):   print(f"  [OK] {msg}")
def skip(msg): print(f"  [--] {msg}")
def fail(msg, exc=None):
    print(f"  [!!] {msg}")
    if exc:
        print(f"       {type(exc).__name__}: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — UoMs
# ─────────────────────────────────────────────────────────────────────────────
print("\n[STEP 1] UoMs")

def find_or_create_uom(name):
    uom = env['uom.uom'].search([('name', '=', name)], limit=1)
    if uom:
        skip(f"UoM '{name}' exists (id={uom.id})")
        return uom
    try:
        uom = env['uom.uom'].create({'name': name})
    except Exception:
        uom = env['uom.uom'].create({'name': name, 'uom_type': 'reference'})
    ok(f"UoM '{name}' CREATED (id={uom.id})")
    return uom

uom_kg    = (env['uom.uom'].search([('name', '=', 'kg')], limit=1)
             or env['uom.uom'].search([('name', 'ilike', 'kg')], limit=1)
             or env['uom.uom'].search([('name', 'ilike', 'kilogram')], limit=1))
if not uom_kg:
    uom_kg = find_or_create_uom('kg')
else:
    skip(f"UoM 'kg' exists (id={uom_kg.id}, name={uom_kg.name})")

uom_ekor  = find_or_create_uom('Ekor')
uom_butir = find_or_create_uom('Butir')   # kept for completeness / shared products

uom_unit = (env['uom.uom'].search([('name', '=', 'Units')], limit=1)
            or env['uom.uom'].search([('name', 'ilike', 'unit')], limit=1))
if not uom_unit:
    uom_unit = find_or_create_uom('Units')
else:
    skip(f"UoM for vaccine exists (id={uom_unit.id}, name={uom_unit.name})")

env.cr.commit()
print("[STEP 1] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Products
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 2] Products")

def find_or_create_product(name, uom, tracked=True):
    tmpl = env['product.template'].search([('name', '=', name)], limit=1)
    if tmpl:
        variant = tmpl.product_variant_ids[:1]
        skip(f"Product '{name}' exists (tmpl={tmpl.id}, var={variant.id})")
        return variant
    tmpl = env['product.template'].create({
        'name': name,
        'type': 'consu',
        'uom_id': uom.id,
        'tracking': 'lot' if tracked else 'none',
    })
    tmpl.is_storable = True   # Odoo 19: must set explicitly
    variant = tmpl.product_variant_ids[:1]
    ok(f"Product '{name}' CREATED (tmpl={tmpl.id}, var={variant.id})")
    return variant

p_dod     = find_or_create_product('Day-Old Duck (DOD)',  uom_ekor,  tracked=True)
p_starter = find_or_create_product('Duck Feed Starter',   uom_kg,    tracked=False)
p_grower  = find_or_create_product('Duck Feed Grower',    uom_kg,    tracked=False)
p_vaccine = find_or_create_product('Duck Vaccine',        uom_unit,  tracked=False)
p_live    = find_or_create_product('Live Duck',           uom_ekor,  tracked=True)
p_meat    = find_or_create_product('Duck Meat',           uom_kg,    tracked=True)
p_manure  = find_or_create_product('Duck Manure',         uom_kg,    tracked=True)

# Fix tracking on bulk products in case they were created with lot in a prior run
for _p in [p_starter, p_grower, p_vaccine]:
    if _p.tracking != 'none':
        _p.product_tmpl_id.tracking = 'none'
        ok(f"Fixed tracking on '{_p.name}' → none")

# Set standard prices so cost report is meaningful
if p_dod.standard_price == 0:
    p_dod.product_tmpl_id.standard_price = 12000.0
    ok("DOD standard_price set to Rp 12,000")

env.cr.commit()
print("[STEP 2] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Masterdata: Division / Site / Zone / Stock location
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 3] Masterdata")

division = env['agri.division'].search([('name', '=', 'Duck Farming')], limit=1)
if not division:
    division = env['agri.division'].create({'name': 'Duck Farming', 'code': 'DUCK'})
    ok(f"Division 'Duck Farming' CREATED (id={division.id})")
else:
    skip(f"Division 'Duck Farming' exists (id={division.id})")

site = env['agri.site'].search(
    [('name', '=', 'Main Farm'), ('division_id', '=', division.id)], limit=1)
if not site:
    site = env['agri.site'].create({'name': 'Main Farm', 'division_id': division.id})
    ok(f"Site 'Main Farm' CREATED (id={site.id})")
else:
    skip(f"Site 'Main Farm' exists (id={site.id})")

# Broiler gets its own zone / location to keep stock separate from layer flock
zone = env['agri.zone'].search(
    [('name', '=', 'Duck House B'), ('site_id', '=', site.id)], limit=1)
if not zone:
    zone = env['agri.zone'].create({
        'name': 'Duck House B',
        'site_id': site.id,
        'zone_type': 'duck_house',
        'capacity': 400,
    })
    ok(f"Zone 'Duck House B' CREATED (id={zone.id})")
else:
    skip(f"Zone 'Duck House B' exists (id={zone.id})")

warehouse = env['stock.warehouse'].search(
    [('company_id', '=', env.company.id)], limit=1)
if not warehouse:
    raise RuntimeError("No warehouse found. Run base setup first.")
wh_stock = warehouse.lot_stock_id
ok(f"Warehouse '{warehouse.name}' — stock: {wh_stock.complete_name}")

flock_loc = env['stock.location'].search([
    ('name', '=', 'Duck House B'),
    ('location_id', '=', wh_stock.id),
    ('usage', '=', 'internal'),
], limit=1)
if not flock_loc:
    flock_loc = env['stock.location'].create({
        'name': 'Duck House B',
        'location_id': wh_stock.id,
        'usage': 'internal',
    })
    ok(f"Stock location 'Duck House B' CREATED (id={flock_loc.id})")
else:
    skip(f"Stock location 'Duck House B' exists (id={flock_loc.id})")

env.cr.commit()
print("[STEP 3] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Stock up feed
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 4] Stocking feed in warehouse")

# Days  1-10: Starter  10 kg/day × 10 = 100 kg
# Days 11-25: Grower   20 kg/day × 15 = 300 kg
# Days 26-45: Grower   25 kg/day × 20 = 500 kg  (finisher phase, same product)
FEED_STOCK = [
    (p_starter, 110.0,   'Duck Feed Starter'),
    (p_grower,  820.0,   'Duck Feed Grower (incl. finisher phase)'),
]

for product, qty_needed, label in FEED_STOCK:
    quants = env['stock.quant'].search([
        ('product_id', '=', product.id),
        ('location_id', '=', wh_stock.id),
    ])
    current_qty = sum(quants.mapped('quantity'))
    if current_qty >= qty_needed:
        skip(f"{label}: {current_qty:.0f} kg already in stock (need {qty_needed:.0f})")
        continue
    to_add = qty_needed - current_qty
    env['stock.quant']._update_available_quantity(product, wh_stock, to_add)
    ok(f"{label}: +{to_add:.0f} kg added (total now {qty_needed:.0f} kg)")

env.cr.commit()
print("[STEP 4] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Purchase Order for 300 DOD at Rp 12,000 → receive with lot
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 5] Purchase Order — 300 DOD at Rp 12,000")

existing_lot = env['stock.lot'].search([
    ('name', '=', LOT_NAME), ('product_id', '=', p_dod.id),
], limit=1)

if existing_lot:
    skip(f"Lot '{LOT_NAME}' already exists (id={existing_lot.id}) — skipping PO")
    dod_lot = existing_lot
else:
    vendor = (env['res.partner'].search([('supplier_rank', '>', 0)], limit=1)
              or env['res.partner'].search([], limit=1))
    if not vendor:
        raise RuntimeError("No partner found.")
    ok(f"Using vendor: {vendor.name} (id={vendor.id})")

    po = env['purchase.order'].create({
        'partner_id': vendor.id,
        'order_line': [(0, 0, {
            'product_id': p_dod.id,
            'product_qty': 300,
            'price_unit': 12000.0,
            'date_planned': str(FLOCK_START),
        })],
    })
    ok(f"Purchase Order created: {po.name}")

    po.button_confirm()
    ok(f"PO confirmed — state: {po.state}")

    dod_lot = env['stock.lot'].create({
        'name': LOT_NAME,
        'product_id': p_dod.id,
        'company_id': env.company.id,
    })
    ok(f"Lot '{LOT_NAME}' CREATED (id={dod_lot.id})")

    picking = po.picking_ids[:1]
    if not picking:
        raise RuntimeError("No receipt picking found after PO confirm.")
    ok(f"Receipt picking: {picking.name} (state={picking.state})")

    if picking.state not in ('assigned', 'done'):
        picking.action_assign()

    for ml in picking.move_line_ids:
        ml.lot_id   = dod_lot.id
        ml.quantity = ml.move_id.product_uom_qty
        ml.picked   = True   # Odoo 19

    picking._action_done()
    ok(f"Receipt validated — picking state: {picking.state}")
    env.cr.commit()

print("[STEP 5] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Create flock batch
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 6] Flock batch")

existing_batch = env['agri.biological.batch'].search(
    [('lot_id', '=', dod_lot.id)], limit=1)

if existing_batch:
    skip(f"Batch for lot '{LOT_NAME}' exists: {existing_batch.name} "
         f"(state={existing_batch.state})")
    batch = existing_batch
    # Fix-up: ensure live_bird_product_id matches lot's product (same guard as layer script)
    if batch.live_bird_product_id != p_dod and batch.state == 'draft':
        batch.live_bird_product_id = p_dod
        env.cr.commit()
        ok("Patched live_bird_product_id → Day-Old Duck (DOD)")
else:
    batch = env['agri.biological.batch'].create({
        'batch_type':           'broiler',
        'division_id':          division.id,
        'site_id':              site.id,
        'zone_id':              zone.id,
        'start_date':           str(FLOCK_START),
        'initial_count':        300,
        'live_bird_product_id': p_dod.id,   # must match dod_lot.product_id
        'lot_id':               dod_lot.id,
        'flock_location_id':    flock_loc.id,
        'receiving_location_id': wh_stock.id,
        'meat_product_id':      p_meat.id,
        'manure_product_id':    p_manure.id,
        # egg_product_id intentionally omitted — broilers don't lay
    })
    ok(f"Flock batch CREATED: {batch.name} (id={batch.id})")
    env.cr.commit()

print("[STEP 6] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Input gate + state transitions
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 7] Input gate — place flock → finishing")

if batch.state == 'draft':
    try:
        batch.action_place_flock()
        env.cr.commit()
        ok(f"Flock placed — state: {batch.state}")
    except Exception as e:
        fail("action_place_flock failed", e)
        raise
else:
    skip(f"Batch already past draft (state={batch.state})")

if batch.state == 'placed':
    try:
        batch.action_start_finishing()   # broiler: placed → finishing
        env.cr.commit()
        ok("Batch transitioned to 'finishing'")
    except Exception as e:
        fail("action_start_finishing failed", e)
        raise
else:
    skip(f"Batch state '{batch.state}' — no finishing transition needed")

print("[STEP 7] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — Simulate 45 days (feed / mortality / manure — no eggs)
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 8] Simulating 45 days of operations...")
print(f"  Flock start: {FLOCK_START}  |  Flock end: {sim_date(45)}\n")

# Feed schedule: (day_from, day_to_inclusive, product, kg_per_day, label)
FEED_SCHEDULE = [
    (1,  10, p_starter, 10.0, 'Starter'),
    (11, 25, p_grower,  20.0, 'Grower'),
    (26, 45, p_grower,  25.0, 'Finisher'),   # same product, higher dose
]

MORTALITY_EVENTS = {
    2:  (2, 'disease'),
    5:  (1, 'unknown'),
    15: (2, 'heat_stress'),
    30: (1, 'disease'),
}

MANURE_DAYS = {7, 14, 21, 28, 35, 42}
MANURE_KG   = 60.0

# Snapshot existing records (idempotent rerun detection)
existing_feed_dates = set(
    env['agri.flock.feed.log']
    .search([('batch_id', '=', batch.id), ('state', '=', 'confirmed')])
    .mapped('date')
)
existing_mortality_dates = set(
    env['agri.flock.mortality']
    .search([('batch_id', '=', batch.id), ('state', '=', 'confirmed')])
    .mapped('date')
)
existing_manure_dates = set(
    env['agri.flock.manure.log']
    .search([('batch_id', '=', batch.id), ('state', '=', 'confirmed')])
    .mapped('date')
)

total_feed_kg   = 0.0
total_manure_kg = 0.0
total_mortality = 0

for day in range(1, 46):
    d = sim_date(day)

    # ── Feed ──────────────────────────────────────────────────────────────
    for day_from, day_to, feed_product, kg_day, phase in FEED_SCHEDULE:
        if day_from <= day <= day_to:
            if d not in existing_feed_dates:
                try:
                    feed_log = env['agri.flock.feed.log'].create({
                        'batch_id':   batch.id,
                        'date':       str(d),
                        'product_id': feed_product.id,
                        'quantity':   kg_day,
                    })
                    feed_log.action_confirm()
                    total_feed_kg += kg_day
                except Exception as e:
                    fail(f"Day {day} feed ({phase} {kg_day}kg)", e)
                    raise
            else:
                total_feed_kg += kg_day
            break

    # ── Mortality ─────────────────────────────────────────────────────────
    if day in MORTALITY_EVENTS:
        qty, cause = MORTALITY_EVENTS[day]
        if d not in existing_mortality_dates:
            try:
                mort = env['agri.flock.mortality'].create({
                    'batch_id': batch.id,
                    'date':     str(d),
                    'quantity': qty,
                    'cause':    cause,
                })
                mort.action_confirm()
                total_mortality += qty
                print(f"  Day {day:2d} ({d}): mortality {qty} ({cause})")
            except Exception as e:
                fail(f"Day {day} mortality {qty} ({cause})", e)
                raise
        else:
            total_mortality += qty

    # ── Manure ────────────────────────────────────────────────────────────
    if day in MANURE_DAYS and d not in existing_manure_dates:
        try:
            manure = env['agri.flock.manure.log'].create({
                'batch_id':     batch.id,
                'date':         str(d),
                'estimated_kg': MANURE_KG,
            })
            manure.action_confirm()
            total_manure_kg += MANURE_KG
            print(f"  Day {day:2d} ({d}): manure capture {MANURE_KG:.0f} kg")
        except Exception as e:
            fail(f"Day {day} manure {MANURE_KG}kg", e)
            raise
    elif day in MANURE_DAYS:
        total_manure_kg += MANURE_KG

    if day % 7 == 0:
        env.cr.commit()
        print(f"  ... committed at day {day}")

env.cr.commit()
print("[STEP 8] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — Harvest ALL remaining birds on day 45
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 9] Harvest — day 45")

harvest_date = sim_date(45)
existing_harvest = env['agri.flock.harvest'].search([
    ('batch_id', '=', batch.id),
    ('state', '=', 'confirmed'),
], limit=1)

if existing_harvest:
    skip(f"Harvest already confirmed (id={existing_harvest.id}, "
         f"{existing_harvest.harvest_count} birds, {existing_harvest.meat_weight_kg} kg meat)")
else:
    # Transition to harvesting state if needed
    if batch.state in ('placed', 'finishing'):
        try:
            batch.action_start_harvesting()
            env.cr.commit()
            ok(f"Batch transitioned to 'harvesting'")
        except Exception as e:
            fail("action_start_harvesting failed", e)
            raise
    elif batch.state == 'harvesting':
        skip("Batch already in 'harvesting' state")
    elif batch.state == 'closed':
        skip("Batch already closed — skipping harvest step")
    else:
        fail(f"Unexpected state before harvest: {batch.state}")
        raise RuntimeError(f"Cannot harvest from state '{batch.state}'")

    if batch.state == 'harvesting':
        birds_to_harvest = batch.current_count
        meat_kg = round(birds_to_harvest * MEAT_KG_PER_BIRD, 1)

        ok(f"Harvesting {birds_to_harvest} birds → {meat_kg} kg meat "
           f"({MEAT_KG_PER_BIRD} kg/bird)")

        try:
            harvest = env['agri.flock.harvest'].create({
                'batch_id':       batch.id,
                'date':           str(harvest_date),
                'harvest_count':  birds_to_harvest,
                'meat_weight_kg': meat_kg,
                'notes':          f'Final harvest — all {birds_to_harvest} remaining birds',
            })
            harvest.action_confirm()
            env.cr.commit()
            ok(f"Harvest confirmed — {batch.current_count} birds remain "
               f"(should be 0), {meat_kg} kg meat in WH/Stock")
        except Exception as e:
            fail("Harvest gate failed", e)
            raise

print("[STEP 9] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10 — Close batch
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 10] Close batch")

if batch.state == 'closed':
    skip(f"Batch already closed (end_date={batch.end_date})")
elif batch.state == 'harvesting':
    try:
        batch.action_close()
        env.cr.commit()
        ok(f"Batch CLOSED — end_date: {batch.end_date}")
    except Exception as e:
        fail("action_close failed", e)
        raise
else:
    fail(f"Unexpected state before close: {batch.state} — skipping")

print("[STEP 10] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 11 — Reconciliation check
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 11] Reconciliation check")
try:
    batch.action_reconciliation_check()
    ok("Reconciliation PASSED — batch count matches stock quant")
except Exception as e:
    # After full harvest, current_count should be 0 and stock quant should be 0.
    # reconciliation_check may raise if there is any residual mismatch.
    fail("Reconciliation issue (inspect manually if this is unexpected)", e)

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
batch.invalidate_recordset()

# Collect confirmed feed by phase
confirmed_feed = env['agri.flock.feed.log'].search([
    ('batch_id', '=', batch.id), ('state', '=', 'confirmed'),
])
starter_total  = sum(l.quantity for l in confirmed_feed if l.product_id == p_starter)
grower_total   = sum(l.quantity for l in confirmed_feed if l.product_id == p_grower)

# Harvest record
confirmed_harvest = env['agri.flock.harvest'].search([
    ('batch_id', '=', batch.id), ('state', '=', 'confirmed'),
])
total_birds_harvested = sum(h.harvest_count  for h in confirmed_harvest)
total_meat_kg         = sum(h.meat_weight_kg for h in confirmed_harvest)

# Manure
confirmed_manure = env['agri.flock.manure.log'].search([
    ('batch_id', '=', batch.id), ('state', '=', 'confirmed'),
])
total_manure_confirmed = sum(m.estimated_kg for m in confirmed_manure)

print()
print("=" * 65)
print("  SIMULATION SUMMARY")
print("=" * 65)
print(f"  Batch             : {batch.name}")
print(f"  Batch state       : {batch.state}")
print(f"  Flock type        : broiler")
print(f"  Start date        : {FLOCK_START}  (Day 1 = {sim_date(1)})")
print(f"  Harvest / close   : Day 45 = {sim_date(45)}")
print()
print(f"  Initial count     : {batch.initial_count:,}")
print(f"  Total mortality   : {batch.cumulative_mortality:,} birds")
print(f"  Birds harvested   : {total_birds_harvested:,}")
print(f"  Current count     : {batch.current_count:,}  (should be 0 — all harvested)")
print()
print(f"  Total feed        : {starter_total + grower_total:,.1f} kg")
print(f"    Starter         : {starter_total:,.1f} kg  (Days 1–10,  10 kg/day)")
print(f"    Grower+Finisher : {grower_total:,.1f} kg  (Days 11–25 @20 / 26–45 @25)")
print()
print(f"  Meat yield        : {total_meat_kg:,.1f} kg  ({total_birds_harvested} birds "
      f"× {MEAT_KG_PER_BIRD} kg/bird)")
print(f"  Total manure      : {total_manure_confirmed:,.0f} kg")
print()
print(f"  DOD cost (std)    : Rp {batch.total_dod_cost:,.0f}")
print(f"  Feed cost (std)   : Rp {batch.total_feed_cost:,.0f}")
print(f"  Mortality loss    : Rp {batch.total_mortality_loss:,.0f}")
print()
print("  NOTE: Batch is CLOSED. Duck Meat is in WH/Stock.")
print("  NOTE: Cost figures use standard_price; cross-check PO for actuals.")
print("=" * 65)
print()
