from odoo import models, fields, api
from odoo.exceptions import UserError


class BiologicalBatch(models.Model):
    _name = 'agri.biological.batch'
    _description = 'Biological Batch'
    _order = 'start_date desc, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Batch Reference', required=True, copy=False, default='New'
    )
    batch_type = fields.Char(string='Batch Type', required=True)
    division_id = fields.Many2one(
        'agri.division', string='Division', required=True, ondelete='restrict'
    )
    site_id = fields.Many2one(
        'agri.site', string='Site', required=True, ondelete='restrict'
    )
    zone_id = fields.Many2one(
        'agri.zone', string='Zone', required=True, ondelete='restrict'
    )
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('harvesting', 'Harvesting'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    # Head counts — current_count is written by gate methods, not computed,
    # so subclasses (agri_duck_ops) can update it in the same transaction.
    initial_count = fields.Integer(string='Initial Count', required=True)
    current_count = fields.Integer(
        string='Current Count',
        help='Updated by lifecycle gate postings. Starts at initial_count.',
    )

    # Anti-drift fields (CLAUDE.md biological WIP rule)
    last_gate_sync = fields.Datetime(
        string='Last Gate Sync', readonly=True,
        help='Timestamp of the last successful lifecycle gate posting.',
    )
    odoo_stock_state = fields.Text(
        string='Stock State (JSON)', readonly=True,
        help='JSON snapshot of relevant stock.quant values at last gate sync.',
    )
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'agri.biological.batch'
                ) or 'New'
            if 'current_count' not in vals:
                vals['current_count'] = vals.get('initial_count', 0)
        return super().create(vals_list)

    # ── State machine ──────────────────────────────────────────────────────

    def action_activate(self):
        """Draft → Active. Requires shed_manager or farm_admin."""
        self._check_gate_access()
        for rec in self:
            if rec.state != 'draft':
                raise UserError(f'Batch {rec.name} is not in Draft state.')
            rec.state = 'active'

    def action_start_harvesting(self):
        """Active → Harvesting."""
        self._check_gate_access()
        for rec in self:
            if rec.state != 'active':
                raise UserError(f'Batch {rec.name} is not in Active state.')
            rec.state = 'harvesting'

    def action_close(self):
        """Active / Harvesting → Closed."""
        self._check_gate_access()
        for rec in self:
            if rec.state not in ('active', 'harvesting'):
                raise UserError(
                    f'Batch {rec.name} cannot be closed from state {rec.state}.'
                )
            rec.state = 'closed'
            if not rec.end_date:
                rec.end_date = fields.Date.today()

    def action_cancel(self):
        """Draft / Active → Cancelled."""
        self._check_gate_access()
        for rec in self:
            if rec.state == 'closed':
                raise UserError(f'Batch {rec.name} is already closed.')
            rec.state = 'cancelled'

    def action_reset_draft(self):
        """Cancelled → Draft (correction only)."""
        self._check_gate_access()
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError('Only cancelled batches can be reset to Draft.')
            rec.state = 'draft'

    # ── Internal helpers ───────────────────────────────────────────────────

    def _check_gate_access(self):
        """Gate postings require shed_manager or farm_admin group."""
        if not (
            self.env.user.has_group('agri_base_masterdata.group_shed_manager')
            or self.env.user.has_group('agri_base_masterdata.group_farm_admin')
            or self.env.su
        ):
            raise UserError(
                'Gate operations require Shed Manager or Farm Administrator access.'
            )
