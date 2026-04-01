# Odoo stock.move API Reference

## Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Description of the move |
| `product_id` | Many2one → product.product | Product being moved |
| `product_uom_qty` | Float | Quantity in product UoM |
| `product_uom` | Many2one → uom.uom | Unit of measure |
| `location_id` | Many2one → stock.location | Source location |
| `location_dest_id` | Many2one → stock.location | Destination location |
| `origin` | Char | Source document reference |
| `state` | Selection | draft/waiting/confirmed/assigned/done/cancel |
| `move_line_ids` | One2many → stock.move.line | Detailed move lines (with lot) |
| `picking_id` | Many2one → stock.picking | Parent picking (optional for direct moves) |
| `company_id` | Many2one → res.company | Company |

## stock.move.line Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | Many2one → product.product | Product |
| `product_uom_id` | Many2one → uom.uom | UoM |
| `quantity` | Float | Done quantity (Odoo 17+; was `qty_done` in older versions) |
| `location_id` | Many2one → stock.location | Source |
| `location_dest_id` | Many2one → stock.location | Destination |
| `lot_id` | Many2one → stock.lot | Lot/serial (required for tracked products) |
| `lot_name` | Char | Lot name (auto-creates lot if lot_id not set) |

## Version Note: quantity vs qty_done

- **Odoo 17+**: Use `quantity` on stock.move.line
- **Odoo 15-16**: Use `qty_done` on stock.move.line

Check your pinned version. If using Odoo 18/19, use `quantity`.

## Creating a Direct Stock Move (No Picking)

For lifecycle gate postings, we create stock moves directly without
going through the picking workflow:

```python
move = self.env['stock.move'].create({
    'name': 'Description',
    'product_id': product.id,
    'product_uom_qty': qty,
    'product_uom': product.uom_id.id,
    'location_id': source_location.id,
    'location_dest_id': dest_location.id,
    'origin': 'Reference document',
    'move_line_ids': [(0, 0, {
        'product_id': product.id,
        'product_uom_id': product.uom_id.id,
        'quantity': qty,
        'location_id': source_location.id,
        'location_dest_id': dest_location.id,
        'lot_id': lot.id,  # Required for tracked products
    })],
})
move._action_confirm()
move._action_assign()
move._action_done()
```

## Move Lifecycle

```
create() → _action_confirm() → _action_assign() → _action_done()
  draft  →    confirmed     →     assigned     →      done
```

- `_action_confirm()` — confirms the move is valid
- `_action_assign()` — reserves stock (checks availability)
- `_action_done()` — validates the move, updates quants

## stock.quant — Checking Stock Levels

```python
# Get quantity of a product at a location
quants = self.env['stock.quant'].search([
    ('product_id', '=', product.id),
    ('location_id', '=', location.id),
])
total_qty = sum(quants.mapped('quantity'))

# With lot filter
quants = self.env['stock.quant'].search([
    ('product_id', '=', product.id),
    ('location_id', '=', location.id),
    ('lot_id', '=', lot.id),
])
```

## stock.lot — Creating Lots

```python
lot = self.env['stock.lot'].create({
    'name': 'LOT-001',
    'product_id': product.id,
    'company_id': company.id,
})
```

## stock.location Types

| Usage | Type Value | Example |
|-------|-----------|---------|
| Physical warehouse | `internal` | WH/Stock |
| Supplier | `supplier` | Partner Locations/Vendors |
| Customer | `customer` | Partner Locations/Customers |
| Production | `production` | Virtual Locations/Production |
| Scrap | `internal` with `scrap_location=True` | Virtual Locations/Scrap |
| Inventory adjustment | `inventory` | Inventory Adjustment |

## Finding Standard Locations

```python
# Warehouse stock location
warehouse = self.env['stock.warehouse'].search([], limit=1)
stock_loc = warehouse.lot_stock_id

# Production location (virtual)
production_loc = self.env['stock.location'].search([
    ('usage', '=', 'production'),
    ('company_id', '=', self.env.company.id),
], limit=1)

# Scrap location
scrap_loc = self.env['stock.location'].search([
    ('scrap_location', '=', True),
    ('company_id', '=', self.env.company.id),
], limit=1)
```
