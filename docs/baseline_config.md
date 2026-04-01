# Baseline Configuration — Gaialangit ERP
## Slice 1: Duck Farming MVP
_Document purpose: manual setup checklist for first-time Odoo configuration. Do not automate until Slice 1 is validated._

---

## 1. Company

| Field | Value |
|-------|-------|
| Company name | PT Gaialangit (or legal entity name) |
| Country | Indonesia |
| Currency | IDR (Indonesian Rupiah) |
| Timezone | Asia/Jakarta (WIB) |
| Language | Indonesian + English |
| Fiscal year | January – December |

**Setup path:** Settings → Companies → edit company record.

---

## 2. Warehouse

### Main warehouse
| Field | Value |
|-------|-------|
| Name | Main Warehouse |
| Short name | WH |
| Address | Farm address |

### Storage locations (standard + custom)
Odoo creates the standard location tree automatically. Add duck-specific virtual locations:

| Location | Type | Parent | Purpose |
|----------|------|--------|---------|
| WH/Input | Internal | WH | Default goods receipt |
| WH/Stock | Internal | WH | Main inventory |
| WH/Output | Internal | WH | Default outgoing |
| Virtual/Duck House | Virtual | Virtual Locations | Biological WIP holding location (one per physical duck house/pen, created when placing a flock batch) |
| Virtual/Production | Virtual | Virtual Locations | Standard consumption location (already exists) |
| Virtual/Scrap | Scrap | — | Standard scrap (already exists) |

**Note:** Duck house virtual locations are created by `agri_duck_ops` when a flock batch is placed. They hold zero real inventory — they are sync markers for the biological model. Standard stock lives in WH/Stock until consumed/output at gates.

**Setup path:** Inventory → Configuration → Warehouses, then Inventory → Configuration → Locations.

---

## 3. Chart of accounts

### Base chart
Install `l10n_id` — this creates the standard Indonesian CoA.

### Duck-specific additions (5 accounts)
Add after `l10n_id` is installed. Assign codes in the 1xx–5xx range consistent with the `l10n_id` numbering convention (verify available codes after install).

| # | Proposed name | Account type | Notes |
|---|--------------|--------------|-------|
| 1 | Biological WIP — Duck | Current Assets | Balance sheet. Manually debited when WIP JE is posted at month-end. |
| 2 | Inventory — Duck Eggs | Current Assets | Finished goods. Odoo standard stock valuation flows here. |
| 3 | Inventory — Duck Meat | Current Assets | Finished goods. Odoo standard stock valuation flows here. |
| 4 | Inventory — Duck Manure | Current Assets | Byproduct inventory. Valued at nominal/estimate. |
| 5 | Abnormal Loss — Duck | Expenses | Debit when mortality exceeds normal threshold or condemned goods. |

**Account codes:** Assign after reviewing `l10n_id` installed accounts to avoid conflict.
**Setup path:** Accounting → Configuration → Chart of Accounts → New.

---

## 4. Journals

Standard journals created by Odoo automatically:
- **Sales Journal** (INV) — customer invoices
- **Purchase Journal** (BILL) — vendor bills
- **Bank Journal** — bank transactions
- **Cash Journal** — cash transactions
- **Exchange Difference** — currency gains/losses

### Additional journal needed for Slice 1
| Journal | Code | Type | Purpose |
|---------|------|------|---------|
| Stock Valuation | STJ | Miscellaneous | Created automatically by `stock_account` for inventory moves |
| WIP Manual Entries | WIP | Miscellaneous | **Create this manually.** Used by finance to post monthly duck WIP journal entries. Default accounts: debit Biological WIP — Duck / credit per business decision. |

**Setup path:** Accounting → Configuration → Journals → New.

---

## 5. Taxes

`l10n_id` installs Indonesian standard taxes. For Slice 1:
- Use default `l10n_id` VAT configurations (PPN 11%)
- Duck feed: check applicable tax exemption status with finance
- DOD/pullet purchase: check applicable tax status
- Do not create custom tax rules yet

**No action required** — `l10n_id` handles this.

---

## 6. Units of Measure

Enable UoM in Inventory settings. Confirm the following exist (created by `l10n_id` + base):

| UoM | Category | Used for |
|-----|----------|---------|
| Head (ekor) | Unit | DOD, pullet, live duck, mortality |
| kg | Weight | Feed, meat, manure |
| Pieces (pcs) | Unit | Eggs (individual) |
| Tray (tray) | Unit | Eggs (30-egg tray — create if absent) |
| Liter | Volume | Vaccines, supplements |
| Bag (sak) | Unit | Feed bags — create if needed (standard unit for 50kg feed sack) |

**Create missing UoMs:** Inventory → Configuration → Units of Measure.

---

## 7. Products

All products: **Storable**, **tracked by Lot**, **no automated replenishment yet**.

### 7.1 Input products (raw materials)

| Product | UoM | UoM purchase | Category | Account (valuation) | Notes |
|---------|-----|-------------|----------|---------------------|-------|
| Day-Old Duck (DOD) | Head | Head | Biological Inputs | Default stock account | Purchased by head, lot = purchase batch |
| Duck Pullet | Head | Head | Biological Inputs | Default stock account | Same as DOD but older birds |
| Duck Feed — Starter | kg | Bag (50kg) | Duck Feed | Default stock account | For DOD age 0–3 weeks |
| Duck Feed — Grower | kg | Bag (50kg) | Duck Feed | Default stock account | For age 3–8 weeks |
| Duck Feed — Layer | kg | Bag (50kg) | Duck Feed | Default stock account | Layer phase |
| Duck Vaccine (generic) | Dose | Vial | Veterinary | Default stock account | Placeholder; split by vaccine type later |

### 7.2 WIP product

| Product | UoM | Category | Account (valuation) | Notes |
|---------|-----|----------|---------------------|-------|
| Live Duck | Head | Biological WIP | Biological WIP — Duck | Never sold directly from standard stock; consumed at meat harvest gate |

### 7.3 Finished goods

| Product | UoM | UoM sales | Category | Account (valuation) | Notes |
|---------|-----|----------|----------|---------------------|-------|
| Duck Egg | Pieces | Tray | Finished Goods | Inventory — Duck Eggs | Lot = collection date + flock batch |
| Duck Meat (whole) | kg | kg | Finished Goods | Inventory — Duck Meat | Lot = harvest date + flock batch |

### 7.4 Byproduct

| Product | UoM | Category | Account (valuation) | Notes |
|---------|-----|----------|---------------------|-------|
| Duck Manure | kg | Byproducts | Inventory — Duck Manure | Lot = capture date + flock batch; valued at estimate |

### Product categories to create

| Category | Parent | Costing method | Notes |
|----------|--------|---------------|-------|
| Biological Inputs | All | Average Cost (AVCO) | DOD, pullets |
| Duck Feed | All | AVCO | All feed types |
| Veterinary | All | AVCO | Vaccines, meds |
| Biological WIP | All | AVCO | Live Duck |
| Finished Goods | All | Standard Price (initially) | Eggs, meat |
| Byproducts | All | Standard Price (initially) | Manure |

**Note:** Costing method is locked per category once stock moves exist. Choose carefully. AVCO is recommended for live inputs. Standard price for finished goods simplifies initial accounting and can be changed after first full cycle.

**Setup path:** Inventory → Configuration → Product Categories, then Inventory → Products → Products.

---

## 8. Locations for duck operations

Create one internal virtual location per physical duck house/pen before the first flock batch. Name convention: `Duck House / [HouseCode]` (e.g., `Duck House / KD-01`).

These locations represent where biological WIP "lives" during the batch. They are also used as the source location for mortality write-offs and the consumption location for feed moves.

---

## 9. Setup sequence (recommended order)

1. Company settings (name, country, currency, timezone)
2. Install `l10n_id` chart (if not already done via `init_db.sh`)
3. Create 5 duck CoA accounts
4. Create WIP Manual Entries journal
5. Enable UoM in settings; create missing UoMs (Tray, Bag)
6. Create product categories (6 categories)
7. Create all 10 products with correct categories, UoMs, and accounts
8. Create duck house virtual locations (one per physical house)
9. Validate: create a test purchase order for DOD, receive goods, confirm lot is assigned

---

## 10. What is NOT configured in Phase 1

- No automated WIP valuation rules
- No landed cost configuration
- No analytic accounts / cost centers
- No custom tax rules
- No Coretax connector
- No reordering rules / MTO routes
- No customer pricing / pricelist
- No sales configuration beyond default
