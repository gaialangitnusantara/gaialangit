"""
simulate_layer_flock.py
=======================
60-day layer flock cycle simulation for Gaialangit ERP.

Run via Odoo shell:
  docker exec -i <odoo_container> odoo-bin shell -d gaialangit --no-http \\
    < scripts/simulate_layer_flock.py

The script is idempotent: find-or-create for all master records.
env.cr.commit() is called after each major step to preserve progress.
The flock is intentionally NOT closed — left active for manual UI testing.

Odoo 19 notes applied throughout:
  - is_storable=True must be set on storable products
  - No uom_po_id on product.template
  - No uom.category model — UoMs are standalone
  - picked=True must be set after _action_assign()
  - Scrap location has usage='inventory' (not scrap_location boolean)
"""

import sys
from datetime import date, timedelta

print()
print("=" * 65)
print("  Gaialangit — Layer Flock 60-Day Simulation")
print("=" * 65)

FLOCK_START = date(2026, 4, 5)  # Simulation day 1

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def sim_date(day_number):
    """Return calendar date for simulation day N (1-indexed)."""
    return FLOCK_START + timedelta(days=day_number - 1)


def egg_qty_for_day(day):
    """Linear ramp: day 25 → 100 eggs, day 60 → 350 eggs."""
    return round(100 + (day - 25) * 250 / 35)


def ok(msg):
    print(f"  [OK] {msg}")


def skip(msg):
    print(f"  [--] {msg}")


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
    # Odoo 19: no uom.category; create standalone.
    # Try without uom_type first; fall back with it if field is required.
    try:
        uom = env['uom.uom'].create({'name': name})
    except Exception:
        try:
            uom = env['uom.uom'].create({'name': name, 'uom_type': 'reference'})
        except Exception as e:
            fail(f"Cannot create UoM '{name}'", e)
            raise
    ok(f"UoM '{name}' CREATED (id={uom.id})")
    return uom

# kg — standard Odoo UoM; search broadly
uom_kg = (
    env['uom.uom'].search([('name', '=', 'kg')], limit=1)
    or env['uom.uom'].search([('name', 'ilike', 'kg')], limit=1)
    or env['uom.uom'].search([('name', 'ilike', 'kilogram')], limit=1)
)
if not uom_kg:
    uom_kg = find_or_create_uom('kg')
else:
    skip(f"UoM 'kg' exists (id={uom_kg.id}, name={uom_kg.name})")

uom_ekor  = find_or_create_uom('Ekor')
uom_butir = find_or_create_uom('Butir')

# Generic unit for vaccine
uom_unit = (
    env['uom.uom'].search([('name', '=', 'Units')], limit=1)
    or env['uom.uom'].search([('name', 'ilike', 'unit')], limit=1)
)
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
    """Find or create a storable, lot-tracked product."""
    tmpl = env['product.template'].search([('name', '=', name)], limit=1)
    if tmpl:
        variant = tmpl.product_variant_ids[:1]
        skip(f"Product '{name}' exists (tmpl={tmpl.id}, var={variant.id})")
        return variant
    # Create template + variant
    vals = {
        'name': name,
        'type': 'consu',       # start as consumable to avoid constraint issues
        'uom_id': uom.id,
        'tracking': 'lot' if tracked else 'none',
    }
    tmpl = env['product.template'].create(vals)
    # Odoo 19: is_storable must be set explicitly after creation
    tmpl.is_storable = True
    variant = tmpl.product_variant_ids[:1]
    ok(f"Product '{name}' CREATED (tmpl={tmpl.id}, var={variant.id})")
    return variant

p_dod     = find_or_create_product('Day-Old Duck (DOD)',    uom_ekor,  tracked=True)
# Feed and vaccine: no lot tracking — bulk material, lot per kg is impractical
p_starter = find_or_create_product('Duck Feed Starter',     uom_kg,    tracked=False)
p_grower  = find_or_create_product('Duck Feed Grower',      uom_kg,    tracked=False)
p_layer   = find_or_create_product('Duck Feed Layer',       uom_kg,    tracked=False)
p_vaccine = find_or_create_product('Duck Vaccine',          uom_unit,  tracked=False)
p_live    = find_or_create_product('Live Duck',             uom_ekor,  tracked=True)
p_egg     = find_or_create_product('Duck Egg',              uom_butir, tracked=True)
p_manure  = find_or_create_product('Duck Manure',           uom_kg,    tracked=True)

# Fixup: feed products may have been created with tracking='lot' in a prior run.
# Patch them now — Odoo allows changing tracking when no open moves exist.
_feed_products = [p_starter, p_grower, p_layer, p_vaccine]
for _p in _feed_products:
    if _p.tracking != 'none':
        _p.product_tmpl_id.tracking = 'none'
        ok(f"Fixed tracking on '{_p.name}' → none")

# Set standard_price for DOD so cost reporting makes sense
if p_dod.standard_price == 0:
    p_dod.product_tmpl_id.standard_price = 15000.0
    ok("DOD standard_price set to Rp 15,000")

env.cr.commit()
print("[STEP 2] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Masterdata: Division / Site / Zone / Stock Location
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 3] Masterdata")

# Division
division = env['agri.division'].search([('name', '=', 'Duck Farming')], limit=1)
if not division:
    division = env['agri.division'].create({'name': 'Duck Farming', 'code': 'DUCK'})
    ok(f"Division 'Duck Farming' CREATED (id={division.id})")
else:
    skip(f"Division 'Duck Farming' exists (id={division.id})")

# Site
site = env['agri.site'].search([
    ('name', '=', 'Main Farm'),
    ('division_id', '=', division.id),
], limit=1)
if not site:
    site = env['agri.site'].create({
        'name': 'Main Farm',
        'division_id': division.id,
    })
    ok(f"Site 'Main Farm' CREATED (id={site.id})")
else:
    skip(f"Site 'Main Farm' exists (id={site.id})")

# Zone
zone = env['agri.zone'].search([
    ('name', '=', 'Duck House A'),
    ('site_id', '=', site.id),
], limit=1)
if not zone:
    zone = env['agri.zone'].create({
        'name': 'Duck House A',
        'site_id': site.id,
        'zone_type': 'duck_house',
        'capacity': 600,
    })
    ok(f"Zone 'Duck House A' CREATED (id={zone.id})")
else:
    skip(f"Zone 'Duck House A' exists (id={zone.id})")

# Warehouse
warehouse = env['stock.warehouse'].search(
    [('company_id', '=', env.company.id)], limit=1
)
if not warehouse:
    raise RuntimeError("No warehouse found. Run base setup first.")
wh_stock = warehouse.lot_stock_id
ok(f"Warehouse '{warehouse.name}' — stock: {wh_stock.complete_name}")

# Flock location: WH/Stock/Duck House A
flock_loc = env['stock.location'].search([
    ('name', '=', 'Duck House A'),
    ('location_id', '=', wh_stock.id),
    ('usage', '=', 'internal'),
], limit=1)
if not flock_loc:
    flock_loc = env['stock.location'].create({
        'name': 'Duck House A',
        'location_id': wh_stock.id,
        'usage': 'internal',
    })
    ok(f"Stock location 'Duck House A' CREATED (id={flock_loc.id})")
else:
    skip(f"Stock location 'Duck House A' exists (id={flock_loc.id})")

env.cr.commit()
print("[STEP 3] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Stock up feed (inventory adjustment — skip if already stocked)
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 4] Stocking feed in warehouse")

# Calculate exact amounts needed
#   Days  1– 7: Starter  15 kg/day × 7  =  105 kg
#   Days  8–21: Grower   25 kg/day × 14 =  350 kg
#   Days 22–60: Layer    30 kg/day × 39 = 1170 kg
FEED_STOCK = [
    (p_starter, 120.0,   'Duck Feed Starter'),
    (p_grower,  360.0,   'Duck Feed Grower'),
    (p_layer,   1200.0,  'Duck Feed Layer'),
]

for product, qty_needed, label in FEED_STOCK:
    # Check existing stock
    quants = env['stock.quant'].search([
        ('product_id', '=', product.id),
        ('location_id', '=', wh_stock.id),
    ])
    current_qty = sum(quants.mapped('quantity'))
    if current_qty >= qty_needed:
        skip(f"{label}: {current_qty} kg already in stock (need {qty_needed})")
        continue
    to_add = qty_needed - current_qty
    try:
        env['stock.quant']._update_available_quantity(
            product, wh_stock, to_add
        )
        ok(f"{label}: +{to_add} kg added (total now {qty_needed} kg)")
    except Exception as e:
        fail(f"Could not add {label} stock", e)
        raise

env.cr.commit()
print("[STEP 4] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Purchase Order for 500 DOD at Rp 15,000 → receive with lot
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 5] Purchase Order — 500 DOD at Rp 15,000")

LOT_NAME = 'DOD-LAYER-SIM-2026-001'

# Check if lot already exists (idempotent run)
existing_lot = env['stock.lot'].search([
    ('name', '=', LOT_NAME),
    ('product_id', '=', p_dod.id),
], limit=1)

if existing_lot:
    skip(f"Lot '{LOT_NAME}' already exists (id={existing_lot.id}) — skipping PO")
    dod_lot = existing_lot
else:
    # Find or create a vendor partner
    vendor = env['res.partner'].search([('supplier_rank', '>', 0)], limit=1)
    if not vendor:
        vendor = env['res.partner'].search([], limit=1)
    if not vendor:
        raise RuntimeError("No partner found. Create at least one contact first.")
    ok(f"Using vendor: {vendor.name} (id={vendor.id})")

    # Create PO
    po = env['purchase.order'].create({
        'partner_id': vendor.id,
        'order_line': [(0, 0, {
            'product_id': p_dod.id,
            'product_qty': 500,
            'price_unit': 15000.0,
            'date_planned': str(FLOCK_START),
        })],
    })
    ok(f"Purchase Order created: {po.name}")

    # Confirm PO (creates receipt)
    po.button_confirm()
    ok(f"PO confirmed — state: {po.state}")

    # Pre-create lot so it can be assigned during receipt
    dod_lot = env['stock.lot'].create({
        'name': LOT_NAME,
        'product_id': p_dod.id,
        'company_id': env.company.id,
    })
    ok(f"Lot '{LOT_NAME}' CREATED (id={dod_lot.id})")

    # Get the receipt picking
    picking = po.picking_ids[:1]
    if not picking:
        raise RuntimeError("No receipt picking found after PO confirm.")
    ok(f"Receipt picking: {picking.name} (state={picking.state})")

    # Assign (move to ready)
    if picking.state not in ('assigned', 'done'):
        picking.action_assign()
    ok(f"Picking state after assign: {picking.state}")

    # Set lot and quantity on move lines
    for ml in picking.move_line_ids:
        ml.lot_id = dod_lot.id
        ml.quantity = ml.move_id.product_uom_qty
        ml.picked = True  # Odoo 19 requirement

    # Validate the receipt
    picking._action_done()
    ok(f"Receipt validated — picking state: {picking.state}")

    env.cr.commit()

print("[STEP 5] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Create flock batch
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 6] Flock batch")

# Check for existing batch with this lot
existing_batch = env['agri.biological.batch'].search([
    ('lot_id', '=', dod_lot.id),
], limit=1)

if existing_batch:
    skip(f"Batch for lot '{LOT_NAME}' exists: {existing_batch.name} (state={existing_batch.state})")
    batch = existing_batch
    # Ensure live_bird_product_id matches the lot's product (fix-up for idempotent reruns).
    # The lot belongs to p_dod; the move line validation requires product == lot.product_id.
    if batch.live_bird_product_id != p_dod and batch.state == 'draft':
        batch.live_bird_product_id = p_dod
        env.cr.commit()
        ok(f"Patched live_bird_product_id → Day-Old Duck (DOD)")
else:
    batch = env['agri.biological.batch'].create({
        'batch_type': 'layer',
        'division_id': division.id,
        'site_id': site.id,
        'zone_id': zone.id,
        'start_date': str(FLOCK_START),
        'initial_count': 500,
        # lot_id comes from the DOD purchase receipt — live_bird_product_id
        # must match that lot's product so stock move lines are consistent.
        'live_bird_product_id': p_dod.id,
        'lot_id': dod_lot.id,
        'flock_location_id': flock_loc.id,
        'receiving_location_id': wh_stock.id,
        'egg_product_id': p_egg.id,
        'manure_product_id': p_manure.id,
    })
    ok(f"Flock batch CREATED: {batch.name} (id={batch.id})")
    env.cr.commit()

print("[STEP 6] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Input gate: place flock (draft → placed)
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 7] Input gate — place flock")

if batch.state == 'draft':
    try:
        batch.action_place_flock()
        env.cr.commit()
        ok(f"Flock placed — state: {batch.state}, placement_date: {batch.placement_date}")
    except Exception as e:
        fail("action_place_flock failed", e)
        raise
else:
    skip(f"Batch already past draft (state={batch.state})")

# Transition to laying (layer flock)
if batch.state == 'placed':
    try:
        batch.action_start_laying()
        env.cr.commit()
        ok(f"Batch transitioned to 'laying'")
    except Exception as e:
        fail("action_start_laying failed", e)
        raise
else:
    skip(f"Batch state is '{batch.state}' — no laying transition needed")

print("[STEP 7] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — Simulate 60 days
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 8] Simulating 60 days of operations...")
print(f"  Flock start: {FLOCK_START}  |  Flock end: {sim_date(60)}\n")

# Feed schedule: (day_from, day_to_inclusive, product, kg_per_day)
FEED_SCHEDULE = [
    (1,  7,  p_starter, 15.0),
    (8,  21, p_grower,  25.0),
    (22, 60, p_layer,   30.0),
]

# Mortality events: {day: (quantity, cause)}
MORTALITY_EVENTS = {
    3:  (3, 'disease'),
    7:  (2, 'unknown'),
    14: (1, 'heat_stress'),
    28: (1, 'disease'),
    45: (1, 'unknown'),
}

# Manure capture days (every 7 days)
MANURE_DAYS = {7, 14, 21, 28, 35, 42, 49, 56}
MANURE_KG   = 100.0

total_feed_kg  = 0.0
total_eggs     = 0
total_manure   = 0.0
total_mortality = 0

# Track which days have already been logged (for idempotent reruns).
# We detect existing feed logs and mortality events by date to avoid duplicates.
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
existing_egg_dates = set(
    env['agri.flock.egg.collection']
    .search([('batch_id', '=', batch.id), ('state', '=', 'confirmed')])
    .mapped('date')
)
existing_manure_dates = set(
    env['agri.flock.manure.log']
    .search([('batch_id', '=', batch.id), ('state', '=', 'confirmed')])
    .mapped('date')
)

for day in range(1, 61):
    d = sim_date(day)

    # ── Feed ──────────────────────────────────────────────────
    for day_from, day_to, feed_product, kg_day in FEED_SCHEDULE:
        if day_from <= day <= day_to:
            if d not in existing_feed_dates:
                try:
                    feed_log = env['agri.flock.feed.log'].create({
                        'batch_id': batch.id,
                        'date': str(d),
                        'product_id': feed_product.id,
                        'quantity': kg_day,
                    })
                    feed_log.action_confirm()
                    total_feed_kg += kg_day
                except Exception as e:
                    fail(f"Day {day} feed ({feed_product.name} {kg_day}kg)", e)
                    raise
            else:
                # Already confirmed in a previous run — count it in totals
                total_feed_kg += kg_day
            break  # Only one feed product per day

    # ── Mortality ─────────────────────────────────────────────
    if day in MORTALITY_EVENTS and d not in existing_mortality_dates:
        qty, cause = MORTALITY_EVENTS[day]
        try:
            mort = env['agri.flock.mortality'].create({
                'batch_id': batch.id,
                'date': str(d),
                'quantity': qty,
                'cause': cause,
            })
            mort.action_confirm()
            total_mortality += qty
            print(f"  Day {day:3d} ({d}): mortality {qty} ({cause})")
        except Exception as e:
            fail(f"Day {day} mortality {qty} ({cause})", e)
            raise
    elif day in MORTALITY_EVENTS:
        qty, _ = MORTALITY_EVENTS[day]
        total_mortality += qty  # Count for summary even if already recorded

    # ── Egg collection (days 25–60) ───────────────────────────
    if 25 <= day <= 60:
        qty_eggs = egg_qty_for_day(day)
        if d not in existing_egg_dates:
            try:
                egg = env['agri.flock.egg.collection'].create({
                    'batch_id': batch.id,
                    'date': str(d),
                    'quantity': qty_eggs,
                    'grade': 'ungraded',
                })
                egg.action_confirm()
                total_eggs += qty_eggs
            except Exception as e:
                fail(f"Day {day} egg collection {qty_eggs}", e)
                raise
        else:
            total_eggs += qty_eggs  # Count for summary

    # ── Manure (every 7 days) ─────────────────────────────────
    if day in MANURE_DAYS and d not in existing_manure_dates:
        try:
            manure = env['agri.flock.manure.log'].create({
                'batch_id': batch.id,
                'date': str(d),
                'estimated_kg': MANURE_KG,
            })
            manure.action_confirm()
            total_manure += MANURE_KG
            print(f"  Day {day:3d} ({d}): manure capture {MANURE_KG} kg")
        except Exception as e:
            fail(f"Day {day} manure {MANURE_KG}kg", e)
            raise
    elif day in MANURE_DAYS:
        total_manure += MANURE_KG  # Count for summary

    # Commit every 7 days to save progress
    if day % 7 == 0:
        env.cr.commit()
        print(f"  ... committed at day {day}")

# Final commit
env.cr.commit()
print("[STEP 8] Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — Reconciliation check
# ─────────────────────────────────────────────────────────────────────────────
print("[STEP 9] Reconciliation check")
try:
    batch.action_reconciliation_check()
    ok("Reconciliation PASSED — batch count matches stock quant")
except Exception as e:
    fail("Reconciliation check raised an issue", e)
    # Non-fatal: print and continue to summary

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
# Refresh batch from DB
batch.invalidate_recordset()

print()
print("=" * 65)
print("  SIMULATION SUMMARY")
print("=" * 65)
print(f"  Batch             : {batch.name}")
print(f"  Batch state       : {batch.state}")
print(f"  Flock type        : layer")
print(f"  Start date        : {FLOCK_START}  (Day 1 = {sim_date(1)})")
print(f"  Last sim day      : Day 60 = {sim_date(60)}")
print()
print(f"  Initial count     : {batch.initial_count:,}")
print(f"  Total mortality   : {batch.cumulative_mortality:,} birds")
print(f"  Current count     : {batch.current_count:,} birds")
print()

# Feed breakdown
confirmed_feed = env['agri.flock.feed.log'].search([
    ('batch_id', '=', batch.id),
    ('state', '=', 'confirmed'),
])
starter_total = sum(
    l.quantity for l in confirmed_feed
    if l.product_id == p_starter
)
grower_total = sum(
    l.quantity for l in confirmed_feed
    if l.product_id == p_grower
)
layer_total = sum(
    l.quantity for l in confirmed_feed
    if l.product_id == p_layer
)
total_feed_confirmed = starter_total + grower_total + layer_total
print(f"  Total feed        : {total_feed_confirmed:,.1f} kg")
print(f"    Starter         : {starter_total:,.1f} kg  (Days 1–7,  15 kg/day)")
print(f"    Grower          : {grower_total:,.1f} kg  (Days 8–21, 25 kg/day)")
print(f"    Layer           : {layer_total:,.1f} kg  (Days 22–60, 30 kg/day)")
print()
print(f"  Total eggs        : {batch.cumulative_eggs:,} butir")
print(f"  Total manure      : {total_manure:,.0f} kg")
print()

# Cost summary
print(f"  DOD cost (std)    : Rp {batch.total_dod_cost:,.0f}")
print(f"  Feed cost (std)   : Rp {batch.total_feed_cost:,.0f}")
print(f"  Mortality loss    : Rp {batch.total_mortality_loss:,.0f}")
print()
print("  NOTE: Flock is ACTIVE — not closed. Proceed with manual UI testing.")
print("  NOTE: Cost figures use standard_price; cross-check PO for actuals.")
print("=" * 65)
print()
