# Gaialangit Integrated Farming ERP — Business Process Flow
## Aligned with Duck-First Build Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BUILD STATUS LEGEND                                      │
│  [ACTIVE]   = In scope for current slice (Duck Farming)                    │
│  [DEFERRED] = Designed but not built until later slice                     │
│  [FUTURE]   = Not yet designed in detail                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## A. ENTERPRISE FOUNDATION [ACTIVE]

```
Company: Gaialangit
    │
    ├── Division: Duck Farming [ACTIVE]
    ├── Division: Hydroponics [DEFERRED]
    ├── Division: Aquaculture [DEFERRED]
    └── Division: Circular Economy [DEFERRED]
        │
        ▼
Physical Hierarchy
    Division → Site → Zone (duck_house / pen)
        │
        ▼
Standard Odoo Foundation [ACTIVE]
    - Inventory (stock)
    - Purchase (purchase + purchase_stock)
    - Sales (sale_management)
    - Accounting (account + l10n_id)
    - Stock Valuation (stock_account)

Standard Odoo Deferred [DEFERRED]
    - MRP
    - Quality
    - Analytic
    - Assets
    - Maintenance
    - Website Sale
```

---

## B. PROCUREMENT — DUCK INPUTS [ACTIVE — STANDARD ODOO ONLY]

```
Operational Need (DOD, feed, vaccines)
    │
    ▼
Purchase Order (standard Odoo)
    │
    ▼
Goods Receipt + Incoming Lot Assignment
    │
    ├── Accepted → Raw Material Inventory
    ├── Rejected → Return to Vendor
    └── Hold (standard quarantine)
    │
    ▼
Vendor Bill → Payment → Reconciliation
    (all standard Odoo AP flow)

Note: Advanced procurement (RFI, RFQ, vendor qualification,
      quotation comparison) is [DEFERRED] to Procurement Extension slice.
```

---

## C. RAW MATERIAL INVENTORY — DUCK [ACTIVE]

```
Raw Material Inventory (official Odoo stock ledger)
    │
    ├── Day-Old Ducks (DOD) / Pullets     [Lot-tracked]
    ├── Duck Feed (Starter/Grower/Layer)   [Lot-tracked]
    ├── Duck Vaccines / Supplements        [Lot-tracked]
    └── Shared consumables                 [As needed]
```

---

## D. DUCK FLOCK OPERATIONS [ACTIVE]

```
NOTE: During active flock lifecycle, operational truth lives in
      custom biological models. Standard Odoo stock is updated
      ONLY at lifecycle gates. Anti-drift sync enforced.

DOD/Pullet in Standard Stock
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│              FLOCK BATCH (Custom Model)                  │
│                                                         │
│  States: draft → placed → laying/finishing              │
│          → harvesting → closed                          │
│                                                         │
│  Fields: initial_head_count, current_head_count,        │
│          batch_type (layer/broiler/breeder),             │
│          zone_id (duck house/pen),                      │
│          last_gate_sync, odoo_stock_state                │
└─────────────────────────────────────────────────────────┘
    │
    ├── INPUT GATE: Transfer DOD/pullet from receiving
    │   stock into flock batch → stock.move created
    │
    ├── CONSUMPTION GATE (daily):
    │   Feed issued from warehouse → stock.move
    │   Cost recorded on batch for reporting
    │
    ├── MORTALITY GATE (as needed):
    │   Dead birds recorded in flock batch
    │   ──── SAME TRANSACTION ────
    │   stock.move: live bird → scrap location
    │   current_head_count recomputed
    │   last_gate_sync updated
    │   ─── ROLLS BACK TOGETHER IF EITHER FAILS ───
    │
    ├── OUTPUT GATE — EGGS (daily, layers only):
    │   Egg count recorded
    │   stock.move: eggs into finished goods
    │   Lot = batch_ref + date
    │
    ├── OUTPUT GATE — MEAT (end of cycle):
    │   Harvest recorded
    │   stock.move: meat into finished goods
    │   Flock batch → harvesting → closed
    │
    └── BYPRODUCT GATE — MANURE (periodic):
        Estimated kg recorded
        stock.move: manure into byproduct inventory
        Lot-tracked for future circular linkage
```

---

## E. LIFECYCLE GATES — STOCK IMPACT SUMMARY [ACTIVE]

```
Gate                  Stock Move Direction                  Odoo Impact
─────────────────────────────────────────────────────────────────────────
Input (DOD)           Receiving → Flock Internal Loc        stock.move
Feed consumption      Warehouse → Production Consume        stock.move
Mortality             Flock Internal Loc → Scrap            stock.move (write-off)
Egg collection        Production → Finished Goods           stock.move
Meat harvest          Production → Finished Goods           stock.move
Manure capture        Production → Byproduct Location       stock.move

Every gate updates flock batch last_gate_sync.
Reconciliation check available at any time.
```

---

## F. RECONCILIATION CHECK [ACTIVE]

```
At any point, compare:
┌──────────────────────────────┬──────────────────────────────┐
│ Biological Model             │ Odoo Standard Stock          │
├──────────────────────────────┼──────────────────────────────┤
│ Flock current_head_count     │ stock.quant for live bird    │
│ Cumulative egg collections   │ stock.move sum for egg prod  │
│ Cumulative feed consumed     │ stock.move sum for feed prod │
│ Cumulative mortality         │ stock.move sum to scrap loc  │
│ Cumulative manure captured   │ stock.move sum for manure    │
└──────────────────────────────┴──────────────────────────────┘
                    │
                    ▼
          Discrepancy? → Flag for investigation
          Match? → System is in sync
```

---

## G. FINANCIAL CLOSE — DUCK [ACTIVE — MANUAL]

```
End of Month
    │
    ▼
Finance opens Batch Cost Summary Report (read-only)
    │
    ├── Per flock batch:
    │   - DOD/pullet cost (from purchase)
    │   - Feed cost (from stock moves)
    │   - Vaccine/supplement cost
    │   - Mortality quantity
    │   - Egg output quantity
    │   - Meat output quantity
    │   - Manure captured
    │
    ▼
Finance creates MANUAL Journal Entry in Odoo
    │
    ├── Dr: Biological WIP — Duck
    │   Cr: WIP cost clearing (or direct cost accounts)
    │
    ├── Dr: Abnormal Loss — Duck (if applicable)
    │   Cr: Biological WIP — Duck
    │
    └── Dr: Finished Goods (Eggs/Meat)
        Cr: Biological WIP — Duck
    │
    ▼
Lock period. Next month starts fresh.

Note: NO automated WIP engine. NO subledger. NO wizards.
      Automation considered only after 3+ manual closes.
```

---

## H. ORDER-TO-CASH — DUCK OUTPUTS [ACTIVE — STANDARD ODOO]

```
Finished Goods Available (Eggs / Meat / Manure)
    │
    ▼
Sales Order (standard Odoo)
    │
    ▼
Delivery / Lot Traceability
    │
    ▼
Customer Invoice
    │
    ▼
Payment → Reconciliation
    (all standard Odoo AR flow)
```

---

## DEFERRED SECTIONS
The following flows are documented in the full PRD but NOT built in Slice 1.

### [DEFERRED] Hydroponic Operations
Crop batch → nursery → transplant → harvest → grading → packing.
Follows same gate pattern as duck. Built in Slice 2.

### [DEFERRED] Aquaculture Operations
Pond batch → stocking → grow-out → harvest.
Follows same gate pattern. Built in Slice 3.

### [DEFERRED] Circular Economy
```
Duck Manure (already in inventory from Slice 1)
    + Aqua Sludge + Melon Biomass + Organic Waste
    │
    ▼
Feedstock Acceptance → Pre-Processing
    │
    ├── Compost Route
    ├── Liquid Nutrient Route
    ├── Vermiculture Route → Vermicompost + Worm Biomass
    │                            └── Worm Processing → Wormmeal
    └── Other Circular Routes

Built in Slice 4 when circular inputs accumulate.
```

### [DEFERRED] IoT Telemetry
```
Sensors → Gateway → Middleware → Time-series DB → Odoo alerts/summaries
Duck house temperature, humidity, airflow entered manually until IoT slice.
Built in Slice 6.
```

### [DEFERRED] Compliance & Reporting
Coretax connector, KPI dashboard, sustainability reporting, traceability portal.
Built in Slice 5-6.

### [FUTURE] WIP Valuation Engine
```
Daily roll-up → EOM wizard → Discrepancy review → Journal posting
Only considered after:
  - 3+ flock cycles completed
  - 2+ manual month-end closes
  - Finance validates CoA against real transactions
See business_process_diagram_wip_reference.md for full design.
```
