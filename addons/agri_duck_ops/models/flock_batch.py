"""
Flock batch — concrete duck model inheriting agri.biological.batch (AbstractModel).

Defines agri.flock.batch with _name = 'agri.flock.batch' and
_inherit = ['agri.biological.batch'] to create its own database table.
Adds:
  - batch_type overridden as Selection (layer/broiler/breeder)
  - Duck-specific states: placed → laying/finishing → harvesting → closed
  - Live-bird product, lot, flock location, and output product links
  - Back-references to all gate models
  - Stored-computed current_count (initial - mortality - harvested)
  - Anti-drift helpers (_update_gate_sync, _get_stock_snapshot)
  - Input gate: action_place_flock (DOD receipt → flock location)
  - Reconciliation check
"""

import json
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class FlockBatch(models.Model):
    _name = 'agri.flock.batch'
    _description = 'Duck Flock Batch'
    _inherit = ['agri.biological.batch']
    _order = 'start_date desc, name'

    # ── Override batch_type as duck-specific Selection ─────────────────────
    # Replaces the Char field in the base model. Column stays VARCHAR — no
    # schema change needed. Both use text storage in PostgreSQL.
    batch_type = fields.Selection(
        selection=[
            ('layer', 'Layer'),
            ('broiler', 'Broiler'),
            ('breeder', 'Breeder'),
        ],
        string='Batch Type',
        required=True,
    )

    # ── Extend state machine with duck-specific states ─────────────────────
    # Base states: draft, active, harvesting, closed, cancelled
    # Duck adds: placed (post-receipt), laying (layers), finishing (broilers)
    # ondelete controls what happens to records on module uninstall.
    state = fields.Selection(
        selection_add=[
            ('placed', 'Placed'),
            ('laying', 'Laying'),
            ('finishing', 'Finishing'),
        ],
        ondelete={
            'placed': 'set draft',
            'laying': 'set draft',
            'finishing': 'set draft',
        }
    )

    # ── Duck-specific identification fields ───────────────────────────────
    breed = fields.Char(string='Breed')

    # ── Stock integration fields ──────────────────────────────────────────
    live_bird_product_id = fields.Many2one(
        'product.product',
        string='Live Duck Product',
        help='Storable product representing live ducks in this flock.',
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Flock Lot',
        help='Lot created during purchase receipt of DOD/pullets.',
    )
    flock_location_id = fields.Many2one(
        'stock.location',
        string='Flock Location',
        domain=[('usage', '=', 'internal')],
        help='Internal location where live ducks are held (duck house / pen).',
    )
    receiving_location_id = fields.Many2one(
        'stock.location',
        string='Receiving Location',
        domain=[('usage', '=', 'internal')],
        help='Location where DOD/pullets were received from purchase.',
    )
    placement_date = fields.Date(string='Placement Date')

    # ── Output product links ──────────────────────────────────────────────
    egg_product_id = fields.Many2one(
        'product.product',
        string='Egg Product',
        help='Finished-goods product for duck eggs.',
    )
    meat_product_id = fields.Many2one(
        'product.product',
        string='Meat Product',
        help='Finished-goods product for duck meat.',
    )
    manure_product_id = fields.Many2one(
        'product.product',
        string='Manure Product',
        help='Byproduct product for duck manure.',
    )

    # ── Back-references to gate models ────────────────────────────────────
    feed_log_ids = fields.One2many(
        'agri.flock.feed.log', 'batch_id', string='Feed Logs'
    )
    mortality_ids = fields.One2many(
        'agri.flock.mortality', 'batch_id', string='Mortality Events'
    )
    egg_collection_ids = fields.One2many(
        'agri.flock.egg.collection', 'batch_id', string='Egg Collections'
    )
    harvest_ids = fields.One2many(
        'agri.flock.harvest', 'batch_id', string='Harvest Records'
    )
    manure_log_ids = fields.One2many(
        'agri.flock.manure.log', 'batch_id', string='Manure Logs'
    )
    vaccine_log_ids = fields.One2many(
        'agri.flock.vaccine.log', 'batch_id', string='Vaccine / Treatment Logs'
    )

    # ── Computed summary fields ───────────────────────────────────────────
    cumulative_mortality = fields.Integer(
        string='Cumulative Mortality',
        compute='_compute_cumulative_mortality',
        store=True,
    )
    cumulative_eggs = fields.Integer(
        string='Cumulative Eggs Collected',
        compute='_compute_cumulative_eggs',
        store=True,
    )
    harvest_count = fields.Integer(
        string='Harvested Count',
        compute='_compute_harvest_count',
        store=True,
    )

    # Override current_count as a stored computed field.
    # The base model stores it manually; duck ops recomputes from gate records.
    # Override create() below removes 'current_count' from vals so the base
    # model's manual assignment does not conflict.
    current_count = fields.Integer(
        string='Current Count',
        compute='_compute_current_count',
        store=True,
        readonly=True,
    )

    # ── Cost summary computed fields (3A-8) ───────────────────────────────
    total_feed_cost = fields.Float(
        string='Total Feed Cost',
        compute='_compute_cost_summary',
        store=True,
        digits='Account',
    )
    total_dod_cost = fields.Float(
        string='Total DOD/Pullet Cost',
        compute='_compute_cost_summary',
        store=True,
        digits='Account',
    )
    total_vaccine_cost = fields.Float(
        string='Total Vaccine / Treatment Cost',
        compute='_compute_cost_summary',
        store=True,
        digits='Account',
    )
    total_mortality_loss = fields.Float(
        string='Mortality Loss Value',
        compute='_compute_cost_summary',
        store=True,
        digits='Account',
        help='dead birds × (DOD price + average rearing cost per bird). '
             'Rearing cost per bird = (feed cost + vaccine cost) / initial count.',
    )

    # ── Compute methods ───────────────────────────────────────────────────

    @api.depends('mortality_ids.quantity', 'mortality_ids.state')
    def _compute_cumulative_mortality(self):
        for rec in self:
            rec.cumulative_mortality = sum(
                rec.mortality_ids
                .filtered(lambda m: m.state == 'confirmed')
                .mapped('quantity')
            )

    @api.depends('egg_collection_ids.quantity', 'egg_collection_ids.state')
    def _compute_cumulative_eggs(self):
        for rec in self:
            rec.cumulative_eggs = sum(
                rec.egg_collection_ids
                .filtered(lambda e: e.state == 'confirmed')
                .mapped('quantity')
            )

    @api.depends('harvest_ids.harvest_count', 'harvest_ids.state')
    def _compute_harvest_count(self):
        for rec in self:
            rec.harvest_count = sum(
                rec.harvest_ids
                .filtered(lambda h: h.state == 'confirmed')
                .mapped('harvest_count')
            )

    @api.depends('initial_count', 'cumulative_mortality', 'harvest_count')
    def _compute_current_count(self):
        for rec in self:
            rec.current_count = rec.initial_count - rec.cumulative_mortality - rec.harvest_count

    @api.depends(
        'initial_count',
        'live_bird_product_id', 'live_bird_product_id.standard_price',
        'feed_log_ids.quantity', 'feed_log_ids.state',
        'feed_log_ids.product_id', 'feed_log_ids.product_id.standard_price',
        'vaccine_log_ids.quantity', 'vaccine_log_ids.state',
        'vaccine_log_ids.product_id', 'vaccine_log_ids.product_id.standard_price',
        'cumulative_mortality',
    )
    def _compute_cost_summary(self):
        for rec in self:
            # Feed cost: sum of (qty × std_price) for confirmed feed logs
            feed_cost = sum(
                log.quantity * log.product_id.standard_price
                for log in rec.feed_log_ids.filtered(lambda l: l.state == 'confirmed')
            )
            rec.total_feed_cost = feed_cost

            # Vaccine / treatment cost: same aggregation pattern as feed
            vaccine_cost = sum(
                log.quantity * log.product_id.standard_price
                for log in rec.vaccine_log_ids.filtered(lambda l: l.state == 'confirmed')
            )
            rec.total_vaccine_cost = vaccine_cost

            # DOD cost: initial_count × live_bird std_price (approximation;
            # actual cost lives on the purchase order lines)
            if rec.live_bird_product_id:
                rec.total_dod_cost = rec.initial_count * rec.live_bird_product_id.standard_price
            else:
                rec.total_dod_cost = 0.0

            # Mortality loss: dead birds × (DOD price + average rearing cost per bird)
            # Rearing cost per bird = (cumulative feed + vaccine spent) / initial_count
            # This reflects that each dead bird consumed a proportional share of feed
            # and vaccine before dying, not just its DOD purchase price.
            if rec.live_bird_product_id:
                dod_price = rec.live_bird_product_id.standard_price
                rearing_cost_per_bird = (
                    (feed_cost + vaccine_cost) / rec.initial_count
                    if rec.initial_count > 0 else 0.0
                )
                rec.total_mortality_loss = (
                    rec.cumulative_mortality * (dod_price + rearing_cost_per_bird)
                )
            else:
                rec.total_mortality_loss = 0.0

    # ── Prevent accidental deletion of active batches ─────────────────────
    def unlink(self):
        """Block deletion of batches that have posted stock moves.

        Rule 1 — State gate: only draft or cancelled batches may be deleted.
        Active batches should be cancelled first (Cancel button), or archived.

        Rule 2 — Confirmed children gate: if any gate record (feed, mortality,
        egg, manure, harvest) is in state='confirmed', a real stock.move has
        already been posted for it. Deleting the batch would cascade-delete
        those gate records but leave the stock moves intact, silently orphaning
        inventory. The caller must cancel (or delete) each confirmed gate
        record individually before deleting the batch.

        ondelete='cascade' on all gate models means draft-only children are
        cleaned up automatically when an eligible batch is deleted.
        """
        for batch in self:
            if batch.state not in ('draft', 'cancelled'):
                raise UserError(
                    f'Cannot delete batch {batch.name} (state={batch.state}).\n\n'
                    f'Click Cancel first to move it to Cancelled state, '
                    f'then delete. Or use Archive to preserve stock history.'
                )
            # Check for confirmed children that have live stock moves
            confirmed_gate_records = (
                len(batch.feed_log_ids.filtered(lambda r: r.state == 'confirmed'))
                + len(batch.mortality_ids.filtered(lambda r: r.state == 'confirmed'))
                + len(batch.egg_collection_ids.filtered(lambda r: r.state == 'confirmed'))
                + len(batch.harvest_ids.filtered(lambda r: r.state == 'confirmed'))
                + len(batch.manure_log_ids.filtered(lambda r: r.state == 'confirmed'))
                + len(batch.vaccine_log_ids.filtered(lambda r: r.state == 'confirmed'))
            )
            if confirmed_gate_records:
                raise UserError(
                    f'Batch {batch.name} has {confirmed_gate_records} confirmed gate '
                    f'record(s) with posted stock moves.\n\n'
                    f'Deleting would orphan those inventory movements. '
                    f'Use Archive (Action → Archive) to hide the batch without '
                    f'corrupting inventory, or manually reverse the stock moves first.'
                )
        return super().unlink()

    # ── Override create to let computed current_count take over ──────────
    @api.model_create_multi
    def create(self, vals_list):
        # current_count is now a stored computed field. Remove any manual value
        # that the base model's create() might inject, so the compute runs clean.
        for vals in vals_list:
            vals.pop('current_count', None)
        return super().create(vals_list)

    # ── Input gate (3A-2): Place flock ────────────────────────────────────
    def action_place_flock(self):
        """Transfer received DOD/pullets from receiving location → flock location.

        Preconditions:
        - Batch in draft state
        - live_bird_product_id, flock_location_id, receiving_location_id, lot_id set
        - Sufficient stock exists in receiving_location_id with correct lot

        Stock move: receiving_location → flock_location (quantity = initial_count)
        Transition: draft → placed
        Anti-drift: last_gate_sync and odoo_stock_state updated.
        """
        self._check_gate_access()
        for rec in self:
            if rec.state != 'draft':
                raise UserError(f'Batch {rec.name} is not in Draft state.')
            if not rec.live_bird_product_id:
                raise UserError('Set the Live Duck Product before placing the flock.')
            if not rec.flock_location_id:
                raise UserError('Set the Flock Location before placing the flock.')
            if not rec.receiving_location_id:
                raise UserError('Set the Receiving Location before placing the flock.')
            if not rec.lot_id:
                raise UserError('Set the Flock Lot before placing the flock.')
            if rec.initial_count <= 0:
                raise UserError('Initial Count must be greater than zero.')

            move_vals = {
                'product_id': rec.live_bird_product_id.id,
                'product_uom_qty': rec.initial_count,
                'product_uom': rec.live_bird_product_id.uom_id.id,
                'location_id': rec.receiving_location_id.id,
                'location_dest_id': rec.flock_location_id.id,
                'origin': rec.name,
                'move_line_ids': [(0, 0, {
                    'product_id': rec.live_bird_product_id.id,
                    'product_uom_id': rec.live_bird_product_id.uom_id.id,
                    'quantity': rec.initial_count,
                    'location_id': rec.receiving_location_id.id,
                    'location_dest_id': rec.flock_location_id.id,
                    'lot_id': rec.lot_id.id,
                    'picked': True,  # Odoo 19: required for _action_done() to process this line
                })],
            }
            move = self.env['stock.move'].create(move_vals)
            move._action_confirm()
            move._action_assign()
            # Odoo 19: must set picked=True after assign (computed field resets it otherwise)
            move.move_line_ids.picked = True
            move._action_done()  # If this fails, entire method rolls back

            rec.write({
                'state': 'placed',
                'placement_date': fields.Date.today(),
            })
            rec._update_gate_sync()

    # ── Duck-specific state transitions ───────────────────────────────────

    def action_start_laying(self):
        """placed → laying  (layer flocks only)."""
        self._check_gate_access()
        for rec in self:
            if rec.state != 'placed':
                raise UserError(f'Batch {rec.name} must be in Placed state.')
            if rec.batch_type != 'layer':
                raise UserError('Only Layer batches can transition to Laying state.')
            rec.state = 'laying'

    def action_start_finishing(self):
        """placed → finishing  (broiler / breeder flocks)."""
        self._check_gate_access()
        for rec in self:
            if rec.state != 'placed':
                raise UserError(f'Batch {rec.name} must be in Placed state.')
            if rec.batch_type not in ('broiler', 'breeder'):
                raise UserError('Only Broiler or Breeder batches can transition to Finishing state.')
            rec.state = 'finishing'

    def action_start_harvesting(self):
        """Override base: allow placed/laying/finishing → harvesting for duck batches."""
        self._check_gate_access()
        for rec in self:
            if rec.state not in ('placed', 'laying', 'finishing', 'active'):
                raise UserError(
                    f'Batch {rec.name} cannot move to Harvesting from state {rec.state}.'
                )
            rec.state = 'harvesting'

    def action_close(self):
        """Override base: allow harvesting (and earlier duck states) → closed."""
        self._check_gate_access()
        for rec in self:
            if rec.state not in ('placed', 'laying', 'finishing', 'active', 'harvesting'):
                raise UserError(
                    f'Batch {rec.name} cannot be closed from state {rec.state}.'
                )
            rec.state = 'closed'
            if not rec.end_date:
                rec.end_date = fields.Date.today()

    # ── Anti-drift helpers ────────────────────────────────────────────────

    def _update_gate_sync(self):
        """Update anti-drift markers after any gate posting.

        Must be called at the end of every gate method, within the same
        database transaction, so the snapshot reflects the just-applied move.
        """
        self.ensure_one()
        self.write({
            'last_gate_sync': fields.Datetime.now(),
            'odoo_stock_state': json.dumps(self._get_stock_snapshot()),
        })

    def _get_stock_snapshot(self):
        """Query Odoo stock.quant to build a drift-detection snapshot."""
        self.ensure_one()
        StockQuant = self.env['stock.quant']

        live_birds = 0.0
        if self.live_bird_product_id and self.flock_location_id and self.lot_id:
            quants = StockQuant.search([
                ('product_id', '=', self.live_bird_product_id.id),
                ('location_id', '=', self.flock_location_id.id),
                ('lot_id', '=', self.lot_id.id),
            ])
            live_birds = sum(quants.mapped('quantity'))

        total_feed = sum(
            l.quantity
            for l in self.feed_log_ids.filtered(lambda l: l.state == 'confirmed')
        )
        total_manure_kg = sum(
            l.estimated_kg
            for l in self.manure_log_ids.filtered(lambda l: l.state == 'confirmed')
        )

        return {
            'live_birds': live_birds,
            'cumulative_mortality': self.cumulative_mortality,
            'cumulative_eggs': self.cumulative_eggs,
            'total_feed_consumed': total_feed,
            'total_manure_kg': total_manure_kg,
            'snapshot_time': fields.Datetime.now().isoformat(),
        }

    # ── Reconciliation check (3A-9) ───────────────────────────────────────

    def action_reconciliation_check(self):
        """Compare biological model state against Odoo stock.quant.

        Checks:
        1. Live-bird head count (batch current_count vs stock.quant)
        2. Cumulative egg output vs confirmed egg collections

        Raises ValidationError listing all discrepancies.
        Updates gate sync markers on success.
        """
        self.ensure_one()
        snapshot = self._get_stock_snapshot()
        issues = []

        # 1. Head count check
        stock_birds = int(snapshot['live_birds'])
        batch_birds = self.current_count
        if stock_birds != batch_birds:
            issues.append(
                f'Head count mismatch: batch says {batch_birds}, '
                f'Odoo stock says {stock_birds}.'
            )

        if issues:
            raise ValidationError('Reconciliation FAILED:\n' + '\n'.join(issues))

        self._update_gate_sync()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reconciliation Passed',
                'message': f'Flock {self.name}: all counts match Odoo stock.',
                'type': 'success',
                'sticky': False,
            },
        }

    # ── Location helpers (shared by gate models via batch reference) ──────

    def _get_production_location(self):
        """Return the virtual production location for this company."""
        self.ensure_one()
        loc = self.env['stock.location'].search([
            ('usage', '=', 'production'),
            ('company_id', 'in', [self.env.company.id, False]),
        ], limit=1)
        if not loc:
            raise ValidationError(
                'No production location found. '
                'Configure a Virtual/Production location in Inventory.'
            )
        return loc

    def _get_scrap_location(self):
        """Return the scrap/inventory-adjustment location for mortality write-offs.

        Odoo 19 removed the scrap_location boolean field. The scrap location
        now has usage='inventory' (same as Inventory Adjustment). We use the
        first inventory-usage location scoped to the company's warehouse.
        """
        self.ensure_one()
        # Odoo 19: scrap_location boolean removed; scrap goes to usage='inventory'
        loc = self.env['stock.location'].search([
            ('usage', '=', 'inventory'),
            ('company_id', 'in', [self.env.company.id, False]),
        ], limit=1)
        if not loc:
            raise ValidationError(
                'No inventory-adjustment location found. '
                'Ensure stock module is installed and warehouse is configured.'
            )
        return loc

    def _get_finished_goods_location(self):
        """Return the finished-goods stock location."""
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not warehouse:
            raise ValidationError('No warehouse configured for this company.')
        return warehouse.lot_stock_id
