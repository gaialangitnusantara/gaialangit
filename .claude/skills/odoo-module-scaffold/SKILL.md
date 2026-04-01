---
name: odoo-module-scaffold
description: "Use this skill whenever you need to create a new Odoo addon module from scratch. Triggers on: 'scaffold addon', 'create module', 'new addon', 'agri_base_masterdata', 'agri_biological_batches', 'agri_duck_ops', or any request to build an Odoo module structure. This skill produces a complete, installable addon skeleton with manifest, models, views, security, and menus — not the minimal output of `odoo scaffold`. Use this instead of writing addon files ad-hoc."
---

# Odoo Module Scaffold Skill

## When to Use
Any time you create a new addon under `addons/`. Never write addon files ad-hoc.
Always follow this structure and checklist.

## Addon Directory Structure

```
addons/<addon_name>/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── <model_name>.py
├── security/
│   ├── security.xml          (groups, categories, record rules)
│   └── ir.model.access.csv   (CRUD permissions per group)
├── views/
│   ├── <model_name>_views.xml  (form + tree + action)
│   └── menus.xml               (menu hierarchy)
├── data/                       (optional — seed data, sequences)
│   └── <data_file>.xml
├── wizard/                     (optional — transient models)
│   ├── __init__.py
│   └── <wizard_name>.py
└── report/                     (optional — QWeb reports)
    ├── __init__.py
    └── <report_name>.xml
```

## File Templates

### `__init__.py` (root)
```python
from . import models
```

If you have wizards:
```python
from . import models
from . import wizard
```

### `__manifest__.py`
```python
{
    'name': 'Agriculture - Module Name',
    'version': '18.0.1.0.0',  # Match pinned Odoo version
    'category': 'Agriculture',
    'summary': 'One-line description',
    'description': """
        Longer description of what this module does.
    """,
    'author': 'Gaialangit',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        # List ALL dependencies — both standard and custom
        # Custom deps: 'agri_base_masterdata', etc.
    ],
    'data': [
        # LOAD ORDER MATTERS. Security first, then views, then data.
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/<model_name>_views.xml',
        # 'data/<data_file>.xml',
    ],
    'installable': True,
    'application': False,  # True only for top-level apps
    'auto_install': False,
}
```

### `models/__init__.py`
```python
from . import <model_name>
```

### `models/<model_name>.py`
```python
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ModelName(models.Model):
    _name = 'agri.<model_name>'
    _description = 'Human Readable Name'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(default=True)

    # Relational fields
    # parent_id = fields.Many2one('agri.parent_model', string='Parent', required=True)

    # Selection fields
    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('active', 'Active'),
    #     ('closed', 'Closed'),
    # ], string='Status', default='draft', required=True)
```

### `security/security.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Reference groups from agri_base_masterdata -->
    <!-- If this IS agri_base_masterdata, define the groups here -->

    <!-- Record rules (optional) -->
    <!--
    <record id="rule_model_user" model="ir.rule">
        <field name="name">Model: User sees own division</field>
        <field name="model_id" ref="model_agri_model_name"/>
        <field name="domain_force">[('division_id','in',user.division_ids.ids)]</field>
        <field name="groups" eval="[(4, ref('agri_base_masterdata.group_farm_operator'))]"/>
    </record>
    -->
</odoo>
```

### `security/ir.model.access.csv`
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_model_operator,agri.model.operator,model_agri_model_name,agri_base_masterdata.group_farm_operator,1,1,1,0
access_model_manager,agri.model.manager,model_agri_model_name,agri_base_masterdata.group_shed_manager,1,1,1,0
access_model_finance,agri.model.finance,model_agri_model_name,agri_base_masterdata.group_finance_user,1,0,0,0
access_model_admin,agri.model.admin,model_agri_model_name,agri_base_masterdata.group_farm_admin,1,1,1,1
```

**Critical rules for access CSV:**
- `model_id:id` format: `model_<model_name_with_underscores>` (dots become underscores)
  - Model `agri.division` → `model_agri_division`
  - Model `agri.flock.batch` → `model_agri_flock_batch`
- `group_id:id` must use full XML ID: `<module_name>.group_name`
- Every model MUST have at least one access rule or install will fail

### `views/<model_name>_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Tree View -->
    <record id="view_agri_model_tree" model="ir.ui.view">
        <field name="name">agri.model.tree</field>
        <field name="model">agri.model_name</field>
        <field name="arch" type="xml">
            <list>
                <field name="name"/>
                <field name="active" optional="hide"/>
            </list>
        </field>
    </record>

    <!-- Form View -->
    <record id="view_agri_model_form" model="ir.ui.view">
        <field name="name">agri.model.form</field>
        <field name="model">agri.model_name</field>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                        </group>
                        <group>
                            <field name="active"/>
                        </group>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Action -->
    <record id="action_agri_model" model="ir.actions.act_window">
        <field name="name">Model Name</field>
        <field name="res_model">agri.model_name</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
```

### `views/menus.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Top-level menu (only in agri_base_masterdata) -->
    <!-- <menuitem id="menu_farming_root" name="Farming" sequence="100"/> -->

    <!-- Sub-menus -->
    <menuitem id="menu_module_root"
              name="Module Section"
              parent="agri_base_masterdata.menu_farming_root"
              sequence="10"/>

    <menuitem id="menu_model_name"
              name="Model Name"
              parent="menu_module_root"
              action="action_agri_model"
              sequence="10"/>
</odoo>
```

## Scaffold Checklist

Before declaring an addon scaffold complete, verify ALL of these:

- [ ] `__manifest__.py` — `depends` lists every required module
- [ ] `__manifest__.py` — `data` lists files in correct order (security → views → data)
- [ ] `__manifest__.py` — version matches pinned Odoo version
- [ ] `models/__init__.py` — imports every model file
- [ ] Root `__init__.py` — imports `models` (and `wizard` if present)
- [ ] `security/ir.model.access.csv` — every model has access rules
- [ ] `security/ir.model.access.csv` — group XML IDs are fully qualified
- [ ] `views/` — every model has tree + form + action
- [ ] `views/menus.xml` — menus reference correct actions and parents
- [ ] XML IDs are unique across the addon
- [ ] No field references nonexistent models or fields

## Install and Validate

After scaffolding:
```bash
./scripts/install_addon.sh <addon_name>
```

If install succeeds:
1. Open Odoo UI
2. Navigate to the addon's menu
3. Create a test record
4. Verify form and list views render correctly

If install fails:
1. Check logs: `docker compose logs odoo | tail -50`
2. Fix the specific error
3. Retry install (no need to restart for XML/data fixes; restart for Python changes)

## Project-Specific Addons

### agri_base_masterdata
- Defines the top-level Farming menu
- Defines all 4 security groups
- Models: `agri.division`, `agri.site`, `agri.zone`
- No dependencies on other custom addons

### agri_biological_batches
- Depends on: `agri_base_masterdata`
- Models: `agri.biological.batch` (base class)
- Provides: state machine, anti-drift fields, computed counts

### agri_duck_ops
- Depends on: `agri_biological_batches`, `stock`
- Models: `agri.flock.batch`, `agri.flock.mortality`, `agri.flock.feed.log`,
          `agri.flock.egg.collection`, `agri.flock.manure.log`
- Each operational model creates `stock.move` on confirm
- See `.claude/skills/odoo-lifecycle-gate/SKILL.md` for gate implementation patterns
