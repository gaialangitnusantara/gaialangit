"""
Mortality gate (3A-4) — CRITICAL same-transaction write-off.

When a mortality event is confirmed:
  1. Create stock.move: flock_location → scrap location (live birds written off)
  2. Write mortality state = confirmed
  3. batch.current_count recomputes automatically (stored computed field)
  4. batch._update_gate_sync() updates anti-drift markers

ANTI-DRIFT CONTRACT: If stock._action_done() fails, the entire method
rolls back. No mortality record is ever confirmed without a matching
stock write-off in the same database transaction.

Never use cr.commit() between steps. Never create the mortality record
outside this gate method. See SKILL.md for full rules.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_ACTIVE_STATES = ('placed', 'laying', 'finishing', 'active', 'harvesting')


class FlockMortality(models.Model):
    _name = 'agri.flock.mortality'
    _description = 'Flock Mortality Event'
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
    quantity = fields.Integer(
        string='Quantity',
        required=True,
    )
    cause = fields.Selection(
        [
            ('disease', 'Disease'),
            ('predator', 'Predator'),
            ('heat_stress', 'Heat Stress'),
            ('unknown', 'Unknown'),
            ('other', 'Other'),
        ],
        string='Cause',
        required=True,
        default='unknown',
    )
    notes = fields.Text(string='Notes')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed')],
        default='draft',
        required=True,
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Write-off Move',
        readonly=True,
        copy=False,
    )

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('batch_id.name', 'date', 'quantity', 'cause')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.batch_id.name or ''} / "
                f"{str(rec.date) if rec.date else ''} / "
                f"{rec.quantity} ({rec.cause or ''})"
            )

    # ── Gate method (CRITICAL) ────────────────────────────────────────────

    def action_confirm(self):
        """Confirm mortality: stock write-off in the SAME transaction.

        Validates:
        - Record is in draft
        - Batch is active
        - quantity > 0
        - quantity <= batch.current_count

        Creates:
        - stock.move: batch.flock_location_id → scrap location
        - move_line with batch.lot_id (lot-tracked birds)

        After _action_done():
        - Sets state = confirmed, move_id
        - batch.cumulative_mortality recomputes (stored computed)
        - batch.current_count recomputes (depends on cumulative_mortality)
        - batch._update_gate_sync() updates anti-drift snapshot

        If _action_done() raises, everything rolls back.
        """
        for rec in self:
            rec.batch_id._check_gate_access()
            if rec.state != 'draft':
                raise UserError('Mortality record is already confirmed.')

            batch = rec.batch_id
            if batch.state not in _ACTIVE_STATES:
                raise UserError(
                    f'Flock batch {batch.name} is not active '
                    f'(current: {batch.state}).'
                )
            if rec.quantity <= 0:
                raise ValidationError('Mortality quantity must be positive.')
            if rec.quantity > batch.current_count:
                raise ValidationError(
                    f'Mortality quantity ({rec.quantity}) exceeds '
                    f'current head count ({batch.current_count}).'
                )
            if not batch.live_bird_product_id:
                raise ValidationError(
                    'Flock batch has no Live Duck Product set. '
                    'Cannot create stock write-off without a product.'
                )
            if not batch.flock_location_id:
                raise ValidationError(
                    'Flock batch has no Flock Location set. '
                    'Cannot create stock write-off without source location.'
                )
            if not batch.lot_id:
                raise ValidationError(
                    'Flock batch has no Flock Lot set. '
                    'Cannot create stock write-off without lot tracking.'
                )

            scrap_loc = batch._get_scrap_location()

            # CRITICAL: stock write-off move MUST be in the same transaction
            move_vals = {
                'product_id': batch.live_bird_product_id.id,
                'product_uom_qty': rec.quantity,
                'product_uom': batch.live_bird_product_id.uom_id.id,
                'location_id': batch.flock_location_id.id,
                'location_dest_id': scrap_loc.id,
                'origin': batch.name,
                'move_line_ids': [(0, 0, {
                    'product_id': batch.live_bird_product_id.id,
                    'product_uom_id': batch.live_bird_product_id.uom_id.id,
                    'quantity': rec.quantity,
                    'location_id': batch.flock_location_id.id,
                    'location_dest_id': scrap_loc.id,
                    'lot_id': batch.lot_id.id,
                    'picked': True,  # Odoo 19: required for _action_done() to process this line
                })],
            }
            move = rec.env['stock.move'].create(move_vals)
            move._action_confirm()
            move._action_assign()
            # Odoo 19: must set picked=True after assign (computed field resets it otherwise)
            move.move_line_ids.picked = True
            move._action_done()  # If this fails → entire method rolls back

            rec.write({'state': 'confirmed', 'move_id': move.id})
            # batch.cumulative_mortality and batch.current_count auto-recompute
            # because mortality_ids.state changed (stored computed with depends)
            batch._update_gate_sync()
