"""
Byproduct gate — manure capture (3A-7).

User records estimated manure output periodically.
On confirm:
  - Generate lot: {batch.name}-MNR-{YYYYMMDD}
  - stock.move: production location → finished goods (byproduct)
    Product: batch.manure_product_id
    Quantity: estimated_kg
  - batch._update_gate_sync()

No routing to circular processing yet — deferred to Slice 4.
Manure is captured as lot-tracked standard inventory for future use.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_ACTIVE_STATES = ('placed', 'laying', 'finishing', 'active', 'harvesting')


class FlockManureLog(models.Model):
    _name = 'agri.flock.manure.log'
    _description = 'Flock Manure Log'
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
        string='Capture Date',
        required=True,
        default=fields.Date.today,
    )
    estimated_kg = fields.Float(
        string='Estimated Weight (kg)',
        required=True,
        digits='Stock Weight',
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
    lot_id = fields.Many2one(
        'stock.lot',
        string='Manure Lot',
        readonly=True,
        copy=False,
        help='Auto-generated from batch name + date on confirm.',
    )

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('batch_id.name', 'date', 'estimated_kg')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.batch_id.name or ''} / "
                f"{str(rec.date) if rec.date else ''} / "
                f"{rec.estimated_kg} kg"
            )

    # ── Gate method ───────────────────────────────────────────────────────

    def action_confirm(self):
        """Confirm manure capture: receive manure into byproduct inventory.

        1. Generate lot: {batch.name}-MNR-{YYYYMMDD}
        2. stock.move: production → finished goods (batch.manure_product_id)
        3. State = confirmed, move_id, lot_id set
        4. batch._update_gate_sync()
        """
        for rec in self:
            rec.batch_id._check_gate_access()
            if rec.state != 'draft':
                raise UserError('Manure log is already confirmed.')

            batch = rec.batch_id
            if batch.state not in _ACTIVE_STATES:
                raise UserError(
                    f'Flock batch {batch.name} is not active '
                    f'(current: {batch.state}).'
                )
            if rec.estimated_kg <= 0:
                raise ValidationError('Estimated weight must be greater than zero.')
            if not batch.manure_product_id:
                raise ValidationError(
                    'Flock batch has no Manure Product set. '
                    'Set it on the flock batch before capturing manure.'
                )

            prod_loc = batch._get_production_location()
            fg_loc = batch._get_finished_goods_location()

            # Generate lot for this capture event
            lot_name = (
                f'{batch.name}-MNR-{rec.date.strftime("%Y%m%d")}'
                if rec.date else f'{batch.name}-MNR'
            )
            lot = rec.env['stock.lot'].create({
                'name': lot_name,
                'product_id': batch.manure_product_id.id,
                'company_id': rec.env.company.id,
            })

            move_vals = {
                'product_id': batch.manure_product_id.id,
                'product_uom_qty': rec.estimated_kg,
                'product_uom': batch.manure_product_id.uom_id.id,
                'location_id': prod_loc.id,
                'location_dest_id': fg_loc.id,
                'origin': batch.name,
                'move_line_ids': [(0, 0, {
                    'product_id': batch.manure_product_id.id,
                    'product_uom_id': batch.manure_product_id.uom_id.id,
                    'quantity': rec.estimated_kg,
                    'location_id': prod_loc.id,
                    'location_dest_id': fg_loc.id,
                    'lot_id': lot.id,
                    'picked': True,  # Odoo 19: required for _action_done() to process this line
                })],
            }
            move = rec.env['stock.move'].create(move_vals)
            move._action_confirm()
            move._action_assign()
            # Odoo 19: must set picked=True after assign (computed field resets it otherwise)
            move.move_line_ids.picked = True
            move._action_done()

            rec.write({
                'state': 'confirmed',
                'move_id': move.id,
                'lot_id': lot.id,
            })
            batch._update_gate_sync()
