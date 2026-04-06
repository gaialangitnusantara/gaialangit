"""
Output gate — meat harvest (3A-6).

End-of-cycle workflow. User records:
  - harvest_count: number of birds harvested
  - meat_weight_kg: estimated meat yield in kg

On confirm:
  1. Move live birds from flock_location → production (consume)
  2. Move meat from production → finished goods (produce)
  3. Generate lot: {batch.name}-MEAT-{YYYYMMDD}
  4. batch.harvest_count recomputes (stored computed)
  5. batch.current_count recomputes (initial - mortality - harvest_count)
  6. batch._update_gate_sync()

Both stock moves must succeed in the same transaction (anti-drift contract).
After harvest the user should transition the batch to closed via action_close().
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class FlockHarvest(models.Model):
    _name = 'agri.flock.harvest'
    _description = 'Flock Meat Harvest'
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
        string='Harvest Date',
        required=True,
        default=fields.Date.today,
    )
    harvest_count = fields.Integer(
        string='Birds Harvested',
        required=True,
    )
    meat_weight_kg = fields.Float(
        string='Meat Yield (kg)',
        digits='Stock Weight',
        help='Estimated total meat weight produced from this harvest.',
    )
    notes = fields.Text(string='Notes')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed')],
        default='draft',
        required=True,
    )
    move_consume_id = fields.Many2one(
        'stock.move',
        string='Live Bird Consumption Move',
        readonly=True,
        copy=False,
    )
    move_meat_id = fields.Many2one(
        'stock.move',
        string='Meat Output Move',
        readonly=True,
        copy=False,
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Meat Lot',
        readonly=True,
        copy=False,
        help='Auto-generated on confirm.',
    )

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('batch_id.name', 'date', 'harvest_count')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.batch_id.name or ''} / "
                f"{str(rec.date) if rec.date else ''} / "
                f"{rec.harvest_count} birds"
            )

    # ── Gate method ───────────────────────────────────────────────────────

    def action_confirm(self):
        """Confirm harvest: consume live birds + receive meat output.

        Two stock moves in the same transaction:
          Move 1 (consume): flock_location → production location
                            product: live_bird, qty: harvest_count, lot: flock lot
          Move 2 (produce): production location → finished goods
                            product: meat_product, qty: meat_weight_kg, lot: new

        Both moves are fully created and prepared BEFORE either _action_done()
        is called, ensuring true atomicity. If either _action_done() fails,
        the entire transaction rolls back.
        """
        for rec in self:
            rec.batch_id._check_gate_access()
            if rec.state != 'draft':
                raise UserError('Harvest record is already confirmed.')

            batch = rec.batch_id
            if batch.state not in ('harvesting', 'placed', 'laying', 'finishing', 'active'):
                raise UserError(
                    f'Flock batch {batch.name} must be in Harvesting state '
                    f'(or an active state) to confirm harvest '
                    f'(current: {batch.state}).'
                )
            if rec.harvest_count <= 0:
                raise ValidationError('Birds harvested must be greater than zero.')
            if rec.harvest_count > batch.current_count:
                raise ValidationError(
                    f'Harvest count ({rec.harvest_count}) exceeds '
                    f'current head count ({batch.current_count}).'
                )
            if not batch.live_bird_product_id:
                raise ValidationError('Flock batch has no Live Duck Product set.')
            if not batch.meat_product_id:
                raise ValidationError(
                    'Flock batch has no Meat Product set. '
                    'Set it on the flock batch before confirming harvest.'
                )
            if not batch.flock_location_id:
                raise ValidationError('Flock batch has no Flock Location set.')
            if not batch.lot_id:
                raise ValidationError('Flock batch has no Flock Lot set.')
            if rec.meat_weight_kg <= 0:
                raise ValidationError('Meat yield (kg) must be greater than zero.')

            prod_loc = batch._get_production_location()
            fg_loc = batch._get_finished_goods_location()

            # ── Create Move 1: consume live birds (flock location → production) ──
            move_consume_vals = {
                'product_id': batch.live_bird_product_id.id,
                'product_uom_qty': rec.harvest_count,
                'product_uom': batch.live_bird_product_id.uom_id.id,
                'location_id': batch.flock_location_id.id,
                'location_dest_id': prod_loc.id,
                'origin': batch.name,
                'move_line_ids': [(0, 0, {
                    'product_id': batch.live_bird_product_id.id,
                    'product_uom_id': batch.live_bird_product_id.uom_id.id,
                    'quantity': rec.harvest_count,
                    'location_id': batch.flock_location_id.id,
                    'location_dest_id': prod_loc.id,
                    'lot_id': batch.lot_id.id,
                    'picked': True,  # Odoo 19: required for _action_done()
                })],
            }
            move_consume = rec.env['stock.move'].create(move_consume_vals)
            move_consume._action_confirm()
            move_consume._action_assign()
            move_consume.move_line_ids.picked = True  # Odoo 19: reset after assign

            # ── Generate meat lot ──────────────────────────────────────────────
            lot_name = (
                f'{batch.name}-MEAT-{rec.date.strftime("%Y%m%d")}'
                if rec.date else f'{batch.name}-MEAT'
            )
            lot = rec.env['stock.lot'].create({
                'name': lot_name,
                'product_id': batch.meat_product_id.id,
                'company_id': rec.env.company.id,
            })

            # ── Create Move 2: produce meat (production → finished goods) ──────
            move_meat_vals = {
                'product_id': batch.meat_product_id.id,
                'product_uom_qty': rec.meat_weight_kg,
                'product_uom': batch.meat_product_id.uom_id.id,
                'location_id': prod_loc.id,
                'location_dest_id': fg_loc.id,
                'origin': batch.name,
                'move_line_ids': [(0, 0, {
                    'product_id': batch.meat_product_id.id,
                    'product_uom_id': batch.meat_product_id.uom_id.id,
                    'quantity': rec.meat_weight_kg,
                    'location_id': prod_loc.id,
                    'location_dest_id': fg_loc.id,
                    'lot_id': lot.id,
                    'picked': True,  # Odoo 19: required for _action_done()
                })],
            }
            move_meat = rec.env['stock.move'].create(move_meat_vals)
            move_meat._action_confirm()
            move_meat._action_assign()
            move_meat.move_line_ids.picked = True  # Odoo 19: reset after assign

            # ── Execute both moves — true atomicity: both or neither ───────────
            # If _action_done() fails on either, the entire transaction rolls back.
            move_consume._action_done()
            move_meat._action_done()

            rec.write({
                'state': 'confirmed',
                'move_consume_id': move_consume.id,
                'move_meat_id': move_meat.id,
                'lot_id': lot.id,
            })
            # batch.harvest_count and batch.current_count auto-recompute
            batch._update_gate_sync()
