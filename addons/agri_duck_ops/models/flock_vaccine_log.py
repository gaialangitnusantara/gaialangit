"""
Vaccine / medical treatment gate.

User records each vaccination or medical treatment applied to the flock.
On confirm: stock.move consuming the product from warehouse stock → production.

Cost is accumulated on the batch (total_vaccine_cost) and feeds into the
adjusted mortality loss calculation:
    mortality_loss = dead_birds × (dod_price + (feed_cost + vaccine_cost) / initial_count)

Gate pattern is identical to flock_feed_log:
    Source:      warehouse.lot_stock_id  (WH/Stock)
    Destination: virtual Production location
    Anti-drift:  batch._update_gate_sync() called in same transaction
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_ACTIVE_STATES = ('placed', 'laying', 'finishing', 'active', 'harvesting')


class FlockVaccineLog(models.Model):
    _name = 'agri.flock.vaccine.log'
    _description = 'Flock Vaccine / Medical Treatment Log'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'

    batch_id = fields.Many2one(
        'agri.flock.batch',
        string='Flock Batch',
        required=True,
        ondelete='cascade',
        index=True,
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Vaccine / Medicine',
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
    treatment_type = fields.Selection(
        [
            ('vaccination', 'Vaccination'),
            ('treatment', 'Treatment'),
            ('prophylactic', 'Prophylactic'),
            ('supplement', 'Supplement'),
        ],
        string='Treatment Type',
        required=True,
        default='vaccination',
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Product Lot',
        domain="[('product_id', '=', product_id)]",
        help='Optional — supply if the vaccine/medicine is lot-tracked.',
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

    @api.depends('batch_id.name', 'date', 'product_id.name', 'treatment_type')
    def _compute_display_name(self):
        type_labels = dict(self._fields['treatment_type'].selection)
        for rec in self:
            parts = filter(None, [
                rec.batch_id.name,
                rec.product_id.name,
                str(rec.date) if rec.date else None,
                type_labels.get(rec.treatment_type),
            ])
            rec.display_name = ' / '.join(parts)

    # ── Gate method ───────────────────────────────────────────────────────

    def action_confirm(self):
        """Confirm vaccine/treatment: consume product from warehouse → production.

        Identical gate pattern to flock_feed_log.action_confirm():
          Source:      warehouse.lot_stock_id
          Destination: virtual production location
          lot_id:      forwarded to move line only if set (optional)

        If _action_done() fails (e.g. insufficient stock), the entire method
        rolls back. State stays 'draft' until the move succeeds.
        """
        for rec in self:
            rec.batch_id._check_gate_access()
            if rec.state != 'draft':
                raise UserError('This record is already confirmed.')

            batch = rec.batch_id
            if batch.state not in _ACTIVE_STATES:
                raise UserError(
                    f'Flock batch {batch.name} is not in an active state '
                    f'(current: {batch.state}).'
                )
            if rec.quantity <= 0:
                raise ValidationError('Quantity must be greater than zero.')

            warehouse = rec.env['stock.warehouse'].search(
                [('company_id', '=', rec.env.company.id)], limit=1
            )
            if not warehouse:
                raise ValidationError('No warehouse configured for this company.')
            source_loc = warehouse.lot_stock_id
            prod_loc = batch._get_production_location()

            ml_vals = {
                'product_id': rec.product_id.id,
                'product_uom_id': rec.product_id.uom_id.id,
                'quantity': rec.quantity,
                'location_id': source_loc.id,
                'location_dest_id': prod_loc.id,
                'picked': True,   # Odoo 19: required for _action_done()
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
            # Odoo 19: must re-set picked=True after _action_assign()
            move.move_line_ids.picked = True
            move._action_done()   # Rolls back everything if this fails

            rec.write({'state': 'confirmed', 'move_id': move.id})
            batch._update_gate_sync()
