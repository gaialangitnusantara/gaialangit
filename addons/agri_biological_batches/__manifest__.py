{
    'name': 'Agriculture - Biological Batches',
    'version': '19.0.1.0.0',
    'category': 'Agriculture',
    'summary': 'Generic biological batch base class with state machine and anti-drift fields',
    'author': 'Gaialangit',
    'license': 'LGPL-3',
    'depends': ['agri_base_masterdata', 'mail'],
    'data': [
        'data/sequences.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/biological_batch_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
