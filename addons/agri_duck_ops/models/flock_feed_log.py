"""
Feed consumption gate (3A-3).

User records daily feed consumption per flock batch.
On confirm: stock.move reducing feed from warehouse stock → production location.
Feed cost accumulates on the batch for the cost summary report.

Anti-drift: batch._update_gate_sync() called on confirm (same transaction).
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_ACTIVE_STATES = ('placed', 'laying', 'finishing', 'active', 'harvesting')


class FlockFeedLog(models.Model):
    _name = 'agri.flock.feed.log'
    _description = 'Flock Feed Log'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'

    batch_id = fields.Many2one(
        'agri.biological.batch',
        string='Flock Batch',
        required=True,
        ondelete='restrict',
        index=True,
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Feed Product',
        required=True,
    )
    quantity = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure',
    )
    uom_id = fields.Many2one(
        related='product_id.uom_id',
        string='Unit',
        readonly=True,
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Feed Lot',
        domain="[('product_id', '=', product_id)]",
    )
    notes = fields.Text(string='Notes')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed')],
        default='draft',
        required=True,
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Stock Move',
        readonly=True,
        copy=False,
    )

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('batch_id.name', 'date', 'product_id.name')
    def _compute_display_name(self):
        for rec in self:
            parts = filter(None, [
                rec.batch_id.name,
                rec.product_id.name,
                str(rec.date) if rec.date else None,
            ])
            rec.display_name = ' / '.join(parts)

    # ── Gate method ───────────────────────────────────────────────────────

    def action_confirm(self):
        """Confirm feed log: create stock.move (warehouse stock → production).

        Stock move: warehouse.lot_stock_id → production virtual location
        Quantity: self.quantity of self.product_id
        Lot: self.lot_id (optional — only if feed is lot-tracked)

        If the move fails (e.g. insufficient stock), the entire method
        rolls back including the state change on this record.
        """
        for rec in self:
            if rec.state != 'draft':
                raise UserError(f'Feed log is already confirmed.')

            batch = rec.batch_id
            if batch.state not in _ACTIVE_STATES:
                raise UserError(
                    f'Flock batch {batch.name} is not in an active state '
                    f'(current: {batch.state}).'
                )
            if rec.quantity <= 0:
                raise ValidationError('Quantity must be greater than zero.')

            # Source: warehouse stock location
            warehouse = rec.env['stock.warehouse'].search([
                ('company_id', '=', rec.env.company.id)
            ], limit=1)
            if not warehouse:
                raise ValidationError('No warehouse configured for this company.')
            source_loc = warehouse.lot_stock_id

            # Destination: virtual production location (consumption)
            prod_loc = batch._get_production_location()

            # Odoo 19: always create move line with picked=True so _action_done() processes it
            ml_vals = {
                'product_id': rec.product_id.id,
                'product_uom_id': rec.product_id.uom_id.id,
                'quantity': rec.quantity,
                'location_id': source_loc.id,
                'location_dest_id': prod_loc.id,
                'picked': True,
            }
            if rec.lot_id:
                ml_vals['lot_id'] = rec.lot_id.id

            move_vals = {
                'product_id': rec.product_id.id,
                'product_uom_qty': rec.quantity,
                'product_uom': rec.product_id.uom_id.id,
                'location_id': source_loc.id,
                'location_dest_id': prod_loc.id,
                'origin': batch.name,
                'move_line_ids': [(0, 0, ml_vals)],
            }

            move = rec.env['stock.move'].create(move_vals)
            move._action_confirm()
            move._action_assign()
            if move.state not in ('assigned', 'confirmed'):
                raise ValidationError(
                    f'Insufficient stock of {rec.product_id.name} at {source_loc.complete_name}. '
                    f'Receive feed into warehouse before confirming consumption.'
                )
            # Odoo 19: must set picked=True after assign (computed field resets it otherwise)
            move.move_line_ids.picked = True
            move._action_done()  # Rolls back everything if this fails

            rec.write({'state': 'confirmed', 'move_id': move.id})
            batch._update_gate_sync()
