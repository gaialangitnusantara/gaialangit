"""
Output gate — egg collection (3A-5).

User records daily egg count, grade, and collection date.
On confirm:
  - Generate lot: {batch.name}-EGG-{YYYYMMDD}
  - stock.move: production location → finished goods location
  - batch.cumulative_eggs recomputes (stored computed)
  - batch._update_gate_sync() updates anti-drift markers
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_ACTIVE_STATES = ('placed', 'laying', 'finishing', 'active', 'harvesting')


class FlockEggCollection(models.Model):
    _name = 'agri.flock.egg.collection'
    _description = 'Flock Egg Collection'
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
        string='Collection Date',
        required=True,
        default=fields.Date.today,
    )
    quantity = fields.Integer(
        string='Quantity (eggs)',
        required=True,
    )
    grade = fields.Selection(
        [
            ('a', 'Grade A'),
            ('b', 'Grade B'),
            ('c', 'Grade C'),
            ('ungraded', 'Ungraded'),
        ],
        string='Grade',
        default='ungraded',
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
        string='Egg Lot',
        readonly=True,
        copy=False,
        help='Auto-generated from batch name + collection date on confirm.',
    )

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('batch_id.name', 'date', 'quantity')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.batch_id.name or ''} / "
                f"{str(rec.date) if rec.date else ''} / "
                f"{rec.quantity} eggs"
            )

    # ── Gate method ───────────────────────────────────────────────────────

    def action_confirm(self):
        """Confirm egg collection: receive eggs into finished goods.

        1. Generate lot: {batch.name}-EGG-{YYYYMMDD}
        2. stock.move: production location → finished goods location
           Product: batch.egg_product_id
           Lot: generated above
        3. State = confirmed, move_id, lot_id set
        4. batch.cumulative_eggs recomputes
        5. batch._update_gate_sync()
        """
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Egg collection is already confirmed.')

            batch = rec.batch_id
            if batch.state not in _ACTIVE_STATES:
                raise UserError(
                    f'Flock batch {batch.name} is not active '
                    f'(current: {batch.state}).'
                )
            if rec.quantity <= 0:
                raise ValidationError('Egg quantity must be positive.')
            if not batch.egg_product_id:
                raise ValidationError(
                    'Flock batch has no Egg Product set. '
                    'Set it on the flock batch before collecting eggs.'
                )

            prod_loc = batch._get_production_location()
            fg_loc = batch._get_finished_goods_location()

            # Generate lot for this collection
            lot_name = (
                f'{batch.name}-EGG-{rec.date.strftime("%Y%m%d")}'
                if rec.date else f'{batch.name}-EGG'
            )
            lot = rec.env['stock.lot'].create({
                'name': lot_name,
                'product_id': batch.egg_product_id.id,
                'company_id': rec.env.company.id,
            })

            move_vals = {
                'product_id': batch.egg_product_id.id,
                'product_uom_qty': rec.quantity,
                'product_uom': batch.egg_product_id.uom_id.id,
                'location_id': prod_loc.id,
                'location_dest_id': fg_loc.id,
                'origin': batch.name,
                'move_line_ids': [(0, 0, {
                    'product_id': batch.egg_product_id.id,
                    'product_uom_id': batch.egg_product_id.uom_id.id,
                    'quantity': rec.quantity,
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
