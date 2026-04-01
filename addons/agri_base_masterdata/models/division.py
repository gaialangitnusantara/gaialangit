from odoo import models, fields


class Division(models.Model):
    _name = 'agri.division'
    _description = 'Farm Division'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, size=10)
    active = fields.Boolean(default=True)
    site_ids = fields.One2many('agri.site', 'division_id', string='Sites')

    _code_unique = models.Constraint(
        'UNIQUE(code)', 'Division code must be unique.'
    )
