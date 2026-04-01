---
name: odoo-lifecycle-gate
description: "Use this skill whenever implementing a biological lifecycle gate posting — any operation that bridges custom biological models with standard Odoo stock movements. This includes: receiving livestock into a batch, recording feed consumption, recording mortality with stock write-off, collecting eggs or harvesting meat into finished goods, capturing manure as byproduct, or any similar operation where a custom model event must create a stock.move in the same database transaction. Trigger on: 'gate posting', 'stock sync', 'mortality write-off', 'feed consumption', 'egg collection', 'harvest gate', 'byproduct capture', 'lifecycle gate', or any mention of synchronizing biological batch state with Odoo inventory."
---

# Lifecycle Gate Posting Skill

## Core Principle

A lifecycle gate is the ONLY point where custom biological models interact with
standard Odoo inventory. Every gate posting must:

1. Create/update the biological model record
2. Create the corresponding `stock.move` in Odoo
3. Update the batch anti-drift markers (`last_gate_sync`, `odoo_stock_state`)
4. All in the **same database transaction** — if any part fails, everything rolls back

## Anti-Drift Contract

Every gate method must end with:
```python
batch.write({
    'last_gate_sync': fields.Datetime.now(),
    'odoo_stock_state': json.dumps(batch._get_stock_snapshot()),
})
```

The `_get_stock_snapshot()` method queries `stock.quant` for the batch's
relevant products and locations, returning a dict like:
```python
{
    'live_birds': 450,
    'total_eggs': 12340,
    'total_feed_consumed': 8500.0,
    'total_manure': 2100.0,
}
```

## Gate Patterns

### Pattern 1: Input Gate (Receive into Batch)

Use when: DOD/pullets arrive from purchase and are placed into a flock batch.

```python
def action_place_flock(self):
    """Transfer received birds from stock into flock batch."""
    self.ensure_one()
    if self.state != 'draft':
        raise ValidationError("Flock must be in draft state to place birds.")

    # 1. Create stock move: receiving location → flock internal location
    move_vals = {
        'name': f'Place flock: {self.name}',
        'product_id': self.live_bird_product_id.id,
        'product_uom_qty': self.initial_head_count,
        'product_uom': self.live_bird_product_id.uom_id.id,
        'location_id': self.receiving_location_id.id,
        'location_dest_id': self.flock_location_id.id,
        'origin': self.name,
        'move_line_ids': [(0, 0, {
            'product_id': self.live_bird_product_id.id,
            'product_uom_id': self.live_bird_product_id.uom_id.id,
            'quantity': self.initial_head_count,
            'location_id': self.receiving_location_id.id,
            'location_dest_id': self.flock_location_id.id,
            'lot_id': self.lot_id.id,
        })],
    }
    move = self.env['stock.move'].create(move_vals)
    move._action_confirm()
    move._action_assign()
    move._action_done()

    # 2. Update batch state
    self.write({
        'state': 'placed',
        'placement_date': fields.Date.today(),
        'last_gate_sync': fields.Datetime.now(),
    })

    return True
```

**Key points:**
- `move._action_done()` validates the move immediately (no picking workflow)
- Lot must exist before placement (created during purchase receipt)
- If `_action_done()` raises, the whole method rolls back

### Pattern 2: Consumption Gate (Feed/Vaccine)

Use when: Daily feed or vaccine is issued from warehouse to flock.

```python
def action_confirm_feed(self):
    """Confirm feed log and create stock consumption move."""
    self.ensure_one()
    if self.state != 'draft':
        raise ValidationError("Feed log already confirmed.")

    batch = self.batch_id
    if batch.state not in ('placed', 'laying', 'finishing'):
        raise ValidationError("Flock batch is not active.")

    # 1. Create stock move: warehouse → production consumption
    move_vals = {
        'name': f'Feed: {batch.name} - {self.date}',
        'product_id': self.product_id.id,
        'product_uom_qty': self.quantity,
        'product_uom': self.product_id.uom_id.id,
        'location_id': self.warehouse_location_id.id,
        'location_dest_id': self.consumption_location_id.id,
        'origin': batch.name,
    }
    move = self.env['stock.move'].create(move_vals)
    move._action_confirm()
    move._action_assign()
    move._action_done()

    # 2. Update feed log state and batch sync
    self.write({'state': 'confirmed', 'move_id': move.id})
    batch._update_gate_sync()

    return True
```

**Key points:**
- `consumption_location_id` should be a virtual production location
- Feed cost is derived from the product's standard price × quantity
- The batch `_update_gate_sync()` helper handles anti-drift update

### Pattern 3: Mortality Gate (Critical — Same-Transaction Write-Off)

Use when: Dead birds are recorded. This is the most critical gate because
a mismatch here creates permanent shadow ledger drift.

```python
def action_confirm_mortality(self):
    """Confirm mortality and create synchronized stock write-off."""
    self.ensure_one()
    if self.state != 'draft':
        raise ValidationError("Mortality already confirmed.")

    batch = self.batch_id
    if batch.state not in ('placed', 'laying', 'finishing'):
        raise ValidationError("Flock batch is not active.")

    if self.quantity <= 0:
        raise ValidationError("Mortality quantity must be positive.")

    if self.quantity > batch.current_head_count:
        raise ValidationError(
            f"Mortality ({self.quantity}) exceeds current head count "
            f"({batch.current_head_count})."
        )

    # 1. Create stock write-off: flock location → scrap location
    #    This MUST be in the same transaction as the mortality record.
    move_vals = {
        'name': f'Mortality: {batch.name} - {self.date} ({self.cause})',
        'product_id': batch.live_bird_product_id.id,
        'product_uom_qty': self.quantity,
        'product_uom': batch.live_bird_product_id.uom_id.id,
        'location_id': batch.flock_location_id.id,
        'location_dest_id': self._get_scrap_location().id,
        'origin': batch.name,
        'move_line_ids': [(0, 0, {
            'product_id': batch.live_bird_product_id.id,
            'product_uom_id': batch.live_bird_product_id.uom_id.id,
            'quantity': self.quantity,
            'location_id': batch.flock_location_id.id,
            'location_dest_id': self._get_scrap_location().id,
            'lot_id': batch.lot_id.id,
        })],
    }
    move = self.env['stock.move'].create(move_vals)
    move._action_confirm()
    move._action_assign()
    move._action_done()  # If this fails, mortality record also rolls back

    # 2. Update mortality record
    self.write({
        'state': 'confirmed',
        'move_id': move.id,
    })

    # 3. Recompute batch head count and sync
    # current_head_count is a computed field:
    #   initial_head_count - sum(confirmed mortality quantities)
    batch._update_gate_sync()

    return True

def _get_scrap_location(self):
    """Get the scrap/loss location for mortality write-offs."""
    scrap_loc = self.env['stock.location'].search([
        ('scrap_location', '=', True),
        ('company_id', '=', self.batch_id.company_id.id),
    ], limit=1)
    if not scrap_loc:
        raise ValidationError("No scrap location configured. Contact admin.")
    return scrap_loc
```

**Critical rules for mortality gate:**
- NEVER create the mortality record without the stock move
- NEVER use `cr.commit()` between mortality creation and stock move
- The lot_id on the move line must match the flock batch lot
- `current_head_count` must be a computed field (not stored manually) to prevent drift
- Always validate quantity ≤ current_head_count before proceeding

### Pattern 4: Output Gate (Eggs / Meat → Finished Goods)

Use when: Eggs are collected daily or meat is harvested at end of cycle.

```python
def action_confirm_egg_collection(self):
    """Confirm egg collection and receive into finished goods."""
    self.ensure_one()
    if self.state != 'draft':
        raise ValidationError("Collection already confirmed.")

    batch = self.batch_id

    # 1. Generate lot for this collection
    lot_name = f'{batch.name}-EGG-{self.date.strftime("%Y%m%d")}'
    lot = self.env['stock.lot'].create({
        'name': lot_name,
        'product_id': self.egg_product_id.id,
        'company_id': batch.company_id.id,
    })

    # 2. Create stock move: production → finished goods
    move_vals = {
        'name': f'Eggs: {batch.name} - {self.date}',
        'product_id': self.egg_product_id.id,
        'product_uom_qty': self.quantity,
        'product_uom': self.egg_product_id.uom_id.id,
        'location_id': self._get_production_location().id,
        'location_dest_id': self.finished_goods_location_id.id,
        'origin': batch.name,
        'move_line_ids': [(0, 0, {
            'product_id': self.egg_product_id.id,
            'product_uom_id': self.egg_product_id.uom_id.id,
            'quantity': self.quantity,
            'location_id': self._get_production_location().id,
            'location_dest_id': self.finished_goods_location_id.id,
            'lot_id': lot.id,
        })],
    }
    move = self.env['stock.move'].create(move_vals)
    move._action_confirm()
    move._action_assign()
    move._action_done()

    # 3. Update record and batch sync
    self.write({
        'state': 'confirmed',
        'move_id': move.id,
        'lot_id': lot.id,
    })
    batch._update_gate_sync()

    return True
```

### Pattern 5: Byproduct Gate (Manure Capture)

Use when: Manure is periodically estimated and captured into inventory.

```python
def action_confirm_manure(self):
    """Confirm manure capture into byproduct inventory."""
    self.ensure_one()
    if self.state != 'draft':
        raise ValidationError("Manure log already confirmed.")

    batch = self.batch_id

    # 1. Generate lot
    lot_name = f'{batch.name}-MNR-{self.date.strftime("%Y%m%d")}'
    lot = self.env['stock.lot'].create({
        'name': lot_name,
        'product_id': self.manure_product_id.id,
        'company_id': batch.company_id.id,
    })

    # 2. Stock move: production → byproduct location
    move_vals = {
        'name': f'Manure: {batch.name} - {self.date}',
        'product_id': self.manure_product_id.id,
        'product_uom_qty': self.estimated_kg,
        'product_uom': self.manure_product_id.uom_id.id,
        'location_id': self._get_production_location().id,
        'location_dest_id': self.byproduct_location_id.id,
        'origin': batch.name,
        'move_line_ids': [(0, 0, {
            'product_id': self.manure_product_id.id,
            'product_uom_id': self.manure_product_id.uom_id.id,
            'quantity': self.estimated_kg,
            'location_id': self._get_production_location().id,
            'location_dest_id': self.byproduct_location_id.id,
            'lot_id': lot.id,
        })],
    }
    move = self.env['stock.move'].create(move_vals)
    move._action_confirm()
    move._action_assign()
    move._action_done()

    self.write({'state': 'confirmed', 'move_id': move.id, 'lot_id': lot.id})
    batch._update_gate_sync()

    return True
```

## Batch Helper Methods

Every flock batch model should include these helpers:

```python
import json
from odoo import fields

def _update_gate_sync(self):
    """Update anti-drift markers after any gate posting."""
    self.ensure_one()
    self.write({
        'last_gate_sync': fields.Datetime.now(),
        'odoo_stock_state': json.dumps(self._get_stock_snapshot()),
    })

def _get_stock_snapshot(self):
    """Query Odoo stock to build a snapshot for drift detection."""
    self.ensure_one()
    StockQuant = self.env['stock.quant']

    # Live birds in flock location
    bird_quants = StockQuant.search([
        ('product_id', '=', self.live_bird_product_id.id),
        ('location_id', '=', self.flock_location_id.id),
        ('lot_id', '=', self.lot_id.id),
    ])
    live_birds = sum(bird_quants.mapped('quantity'))

    return {
        'live_birds': live_birds,
        'snapshot_time': fields.Datetime.now().isoformat(),
    }
```

## Reconciliation Check

Implement as an action button on the flock batch form:

```python
def action_reconciliation_check(self):
    """Compare biological model state against Odoo stock."""
    self.ensure_one()
    snapshot = self._get_stock_snapshot()
    issues = []

    # Check head count
    if snapshot['live_birds'] != self.current_head_count:
        issues.append(
            f"Head count mismatch: Batch says {self.current_head_count}, "
            f"Stock says {snapshot['live_birds']}"
        )

    if issues:
        raise ValidationError(
            "Reconciliation FAILED:\n" + "\n".join(issues)
        )

    # Update sync marker on success
    self._update_gate_sync()

    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Reconciliation Passed',
            'message': f'Flock {self.name}: all counts match Odoo stock.',
            'type': 'success',
        }
    }
```

## Location Strategy

For duck operations, you need these Odoo stock locations:

| Location | Type | Purpose |
|----------|------|---------|
| WH/Stock | Internal | General warehouse for feed, vaccines |
| WH/Stock/Receiving | Internal | Incoming goods from purchase |
| WH/Production | Virtual/Production | Source for finished goods receipt |
| WH/Stock/Finished Goods | Internal | Eggs, meat after harvest |
| WH/Stock/Byproduct | Internal | Manure storage |
| Virtual/Flock/<batch> | Internal | Per-batch bird holding (or one shared flock location) |
| Virtual/Scrap | Scrap | Mortality write-off destination |

**Design decision — per-batch vs shared flock location:**
- Per-batch locations give cleaner quant separation but create many locations
- A shared flock location with lot-based tracking is simpler
- Recommendation: Use a single "Duck Flock" internal location with lot tracking
  to distinguish batches. This avoids location sprawl.

## Common Mistakes

| Mistake | Why It's Bad | Correct Approach |
|---------|-------------|------------------|
| Using `cr.commit()` mid-gate | Breaks transaction atomicity | Let Odoo handle commits |
| Creating move without `_action_done()` | Move stays draft, stock not updated | Always call the full chain |
| Storing `current_head_count` manually | Drift if someone edits directly | Use `@api.depends` computed field |
| Forgetting lot on move lines | Lot tracking breaks | Always pass `lot_id` for tracked products |
| Skipping `_update_gate_sync()` | Anti-drift markers go stale | Call it at end of every gate method |
| Hard-coding location IDs | Breaks on different databases | Use `self.env.ref()` or search |

## For More Details

Read `references/stock_move_api.md` for Odoo stock.move field reference.
Read `references/location_types.md` for Odoo location type details.
