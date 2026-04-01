from odoo import models, fields


class Zone(models.Model):
    _name = 'agri.zone'
    _description = 'Farm Zone'
    _order = 'site_id, name'

    name = fields.Char(string='Name', required=True)
    site_id = fields.Many2one(
        'agri.site', string='Site', required=True, ondelete='restrict'
    )
    division_id = fields.Many2one(
        related='site_id.division_id', store=True, string='Division', readonly=True
    )
    zone_type = fields.Selection([
        ('duck_house', 'Duck House'),
        ('pen', 'Pen'),
        ('greenhouse', 'Greenhouse'),
        ('pond', 'Pond'),
        ('processing', 'Processing'),
        ('other', 'Other'),
    ], string='Zone Type', required=True)
    capacity = fields.Integer(string='Capacity (head / units)')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')
