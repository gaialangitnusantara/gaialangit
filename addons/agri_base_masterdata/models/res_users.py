from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Shed manager: assigned to exactly one site (1:1 per security design)
    site_id = fields.Many2one(
        'agri.site',
        string='Assigned Site',
        help='Farm site assigned to this shed manager (1:1 assignment).',
    )
    # Farm operator: assigned to one or more zones within a site
    zone_ids = fields.Many2many(
        'agri.zone',
        'res_users_agri_zone_rel',
        'user_id',
        'zone_id',
        string='Assigned Zones',
        help='Duck house / pen zones assigned to this operator.',
    )
