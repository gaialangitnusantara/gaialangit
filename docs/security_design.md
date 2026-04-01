# Security Groups Design — Gaialangit ERP
## Slice 1: Duck Farming MVP
_Document purpose: design reference for security groups to be implemented in `agri_base_masterdata`. This is a design doc, not code._

---

## 1. Group definitions

### 1.1 `group_farm_operator`
**Category:** Gaialangit Farm Operations
**Purpose:** Day-to-day data entry on the farm floor. Limited to recording observations and operational events on active batches. Cannot configure, cannot close batches, cannot access finance.

### 1.2 `group_shed_manager`
**Category:** Gaialangit Farm Operations
**Purpose:** Manages flock batch lifecycle — creates batches, places birds, transitions states, records mortality, triggers gate postings, closes batches. Includes all operator permissions plus lifecycle control. **Each shed manager is assigned to exactly one site (1:1).** Can also create Purchase Orders for farm inputs.

### 1.3 `group_finance_user`
**Category:** Gaialangit Finance
**Purpose:** Views cost summaries and batch data for accounting purposes. Posts manual WIP journal entries. No access to create/modify operational data. **Sees data across ALL divisions — no division filter, no site filter.**

### 1.4 `group_farm_admin`
**Category:** Gaialangit Administration
**Purpose:** Full configuration access. Creates master data (divisions, sites, zones, products). Manages security group assignments. Can perform all operations. No implicit Odoo admin rights — separate from Odoo's built-in `base.group_system`.

---

## 2. Group hierarchy

```
group_farm_admin
    └── includes → group_shed_manager
                       └── includes → group_farm_operator

group_finance_user  (standalone — no farm operation inheritance)
```

**Rationale:** Admin can do everything shed managers can do; shed managers can do everything operators can do. Finance users have a separate read path — they should not accidentally trigger operational gates.

**Odoo implementation:** Use `implied_ids` in group XML definition to express the hierarchy.

---

## 3. Model access matrix

### Legend
- **C** = Create
- **R** = Read
- **W** = Write
- **D** = Delete
- `—` = No access (model invisible to this group)

### 3.1 Custom models (`agri_*`)

| Model | farm_operator | shed_manager | finance_user | farm_admin |
|-------|:---:|:---:|:---:|:---:|
| `agri.division` | R | R | R | CRWD |
| `agri.site` | R | R | R | CRWD |
| `agri.zone` | R | R | R | CRWD |
| `agri.biological.batch` (base) | R | CRWD | R | CRWD |
| `agri.flock.batch` | R | CRWD | R | CRWD |
| `agri.flock.mortality` | CRW | CRWD | R | CRWD |
| `agri.flock.feed.line` | CRW | CRWD | R | CRWD |
| `agri.flock.egg.collection` | CRW | CRWD | R | CRWD |
| `agri.flock.manure.capture` | CRW | CRWD | R | CRWD |
| `agri.flock.health.log` | CRW | CRWD | R | CRWD |
| `agri.flock.batch.cost.summary` (report) | R | R | R | R |

**Notes:**
- `farm_operator` can **create** daily event records (mortality, feed, eggs, manure, health) but cannot **delete** them — corrections go through shed manager.
- `farm_operator` cannot **write** to `agri.flock.batch` directly — they cannot change batch state or head count directly. Those happen via gate methods called by shed_manager.
- `farm_admin` can delete — needed for test data cleanup and configuration errors.

### 3.2 Standard Odoo models (relevant to duck operations)

| Model | farm_operator | shed_manager | finance_user | farm_admin |
|-------|:---:|:---:|:---:|:---:|
| `stock.move` | R | R | R | CRWD |
| `stock.picking` | R | R | R | CRWD |
| `stock.quant` | R | R | R | CRWD |
| `stock.lot` | R | CRW | R | CRWD |
| `product.product` | R | R | R | CRWD |
| `product.template` | R | R | R | CRWD |
| `product.category` | — | R | R | CRWD |
| `purchase.order` | R | CRWD | R | CRWD |
| `purchase.order.line` | R | CRWD | R | CRWD |
| `account.move` (journal entry) | — | — | CRWD | CRWD |
| `account.move.line` | — | — | CRWD | CRWD |
| `account.account` | — | — | R | CRWD |
| `account.journal` | — | — | R | CRWD |
| `res.partner` (vendor/customer) | R | R | CRWD | CRWD |

**Notes:**
- `stock.move` and `stock.picking` are created programmatically by gate methods, never directly by operators. Operator read access is for traceability/reporting only.
- Finance users have no access to operational custom models except read — they use cost summary reports.
- Gate posting methods run with `sudo()` or with the shed_manager's rights for stock operations — this is enforced in code, not just ACL.

### 3.3 Configuration models (agri_base_masterdata scope)

| Model | farm_operator | shed_manager | finance_user | farm_admin |
|-------|:---:|:---:|:---:|:---:|
| `agri.division` | R | R | R | CRWD |
| `agri.site` | R | R | R | CRWD |
| `agri.zone` | R | R | R | CRWD |

Only `farm_admin` may add/edit/delete master data configuration.

---

## 4. Menu visibility design

| Menu area | farm_operator | shed_manager | finance_user | farm_admin |
|-----------|:---:|:---:|:---:|:---:|
| Farm Operations → Daily Entry | ✓ | ✓ | — | ✓ |
| Farm Operations → Flock Batches | read-only | ✓ | — | ✓ |
| Farm Operations → Reports | ✓ | ✓ | ✓ | ✓ |
| Procurement | read-only | ✓ | read-only | ✓ |
| Inventory | read-only | read-only | read-only | ✓ |
| Accounting | — | — | ✓ | ✓ |
| Configuration | — | — | — | ✓ |

---

## 5. Record rules (row-level security)

### Rule: Operators see only their assigned zone
`farm_operator` records in `agri.flock.feed.line`, `agri.flock.egg.collection`, `agri.flock.mortality`, `agri.flock.health.log` are filtered to batches in their assigned zone(s).

_Implementation note:_ Add `zone_ids` M2M on `res.users` (in `agri_base_masterdata`). Record rule: `batch_id.zone_id in user.zone_ids`.

### Rule: Finance users see all batches (read-only, no filter)
Finance needs cross-division visibility for cost reporting.

### Rule: Shed managers see their one site
`shed_manager` has access to batches in their assigned site only. Cross-site access requires `farm_admin`. Assignment is **1:1** — one manager, one site.

_Implementation note:_ Add `site_id` Many2one on `res.users` (in `agri_base_masterdata`). Record rule: `batch_id.site_id = user.site_id`.

### Rule: Farm admin has no row-level restrictions
`farm_admin` bypasses all custom record rules via group priority.

---

## 6. Odoo built-in group mappings

Custom groups combine with standard Odoo groups as follows:

| Custom group | Standard Odoo groups to also assign |
|-------------|-------------------------------------|
| `group_farm_operator` | `base.group_user` (internal user) |
| `group_shed_manager` | `base.group_user`, `stock.group_stock_user`, `purchase.group_purchase_user` |
| `group_finance_user` | `base.group_user`, `account.group_account_user` |
| `group_farm_admin` | `base.group_user`, `stock.group_stock_manager`, `purchase.group_purchase_manager` |

**Note:** `farm_admin` does NOT get `base.group_system` (Odoo technical admin). Technical settings are managed by the Odoo system administrator separately.

---

## 7. Implementation notes for `agri_base_masterdata`

When scaffolding the addon:

1. **Declare groups** in `security/groups.xml` under category `Gaialangit / Farm Operations` and `Gaialangit / Finance`.
2. **Implied hierarchy** via `implied_ids`: `farm_admin` implies `shed_manager`, `shed_manager` implies `farm_operator`.
3. **ACL rows** in `security/ir.model.access.csv` — one row per (model, group) combination for non-default access.
4. **Record rules** in `security/record_rules.xml` — use domain filters referencing `user.zone_ids` / `user.site_ids`.
5. **User fields** — add `zone_ids` (M2M, for operator zone filter) and `site_id` (Many2one, for shed manager site filter) on `res.users` via inheritance in `agri_base_masterdata`.
6. **Menu groups** — each menu item's `groups` attribute references the appropriate group XML ID.

### XML ID naming convention
```
gaialangit_base.group_farm_operator
gaialangit_base.group_shed_manager
gaialangit_base.group_finance_user
gaialangit_base.group_farm_admin
```

(Module technical name for `agri_base_masterdata` is `agri_base_masterdata`; XML IDs will be `agri_base_masterdata.group_*`.)

---

## 8. Locked decisions (2026-04-01)

All business questions confirmed. No open items before coding.

| # | Question | Decision | Impact |
|---|----------|----------|--------|
| 1 | Shed manager ↔ site cardinality | **1:1** — one manager, one site | `site_id` Many2one on `res.users` (not M2M). Record rule uses `= user.site_id`. |
| 2 | Finance visibility scope | **All divisions, no filter** | No record rule on finance_user for batch/division. Finance sees entire dataset. |
| 3 | Who creates Purchase Orders | **shed_manager + farm_admin** | shed_manager gets `purchase.group_purchase_user`. PO matrix updated to CRWD for shed_manager. |
| 4 | Gate posting authorization | **shed_manager + farm_admin** | Gate methods check `user.has_group('agri_base_masterdata.group_shed_manager')`. farm_admin inherits this via implied_ids. |
