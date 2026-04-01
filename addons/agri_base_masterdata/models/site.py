from odoo import models, fields


class Site(models.Model):
    _name = 'agri.site'
    _description = 'Farm Site'
    _order = 'division_id, name'

    name = fields.Char(string='Name', required=True)
    division_id = fields.Many2one(
        'agri.division', string='Division', required=True, ondelete='restrict'
    )
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    zip = fields.Char(string='ZIP')
    country_id = fields.Many2one('res.country', string='Country')
    active = fields.Boolean(default=True)
    zone_ids = fields.One2many('agri.zone', 'site_id', string='Zones')
