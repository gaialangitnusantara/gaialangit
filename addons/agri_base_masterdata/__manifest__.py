{
    'name': 'Agriculture - Base Master Data',
    'version': '19.0.1.0.0',
    'category': 'Agriculture',
    'summary': 'Physical hierarchy (Division / Site / Zone) and farm security groups',
    'author': 'Gaialangit',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        # Load order: security first, then views
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/division_views.xml',
        'views/site_views.xml',
        'views/zone_views.xml',
        'views/res_users_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
