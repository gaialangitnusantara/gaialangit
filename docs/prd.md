# PRD.md
# Gaialangit Integrated Farming ERP

## 1. Vision
Build an Odoo ERP for a multi-sector integrated farming enterprise.
The system will be built incrementally by vertical slice, starting with **duck farming** as the proving ground for all architectural decisions.

Target sectors (in implementation order):
1. Duck farming (eggs, meat, manure byproduct)
2. Hydroponic premium melon
3. Shrimp aquaculture
4. Circular economy processing (compost, vermiculture, worm processing)
5. Cross-cutting: procurement, finance, compliance, IoT, reporting

## 2. Core principle
Standard Odoo is the official transactional ledger for:
- inventory (stock.move, stock.quant, stock.lot)
- procurement (purchase.order)
- sales (sale.order)
- invoicing (account.move — invoice)
- accounting (account.move — journal entry)
- MRP at lifecycle gates

Custom addons hold biological operational truth where standard Odoo is not naturally suited — specifically, the daily state of living biological batches between lifecycle gate events.

**Anti-drift principle:** The custom biological layer and standard Odoo stock must never silently diverge. Every gate posting updates both systems and logs a sync marker. A reconciliation report must be available to compare biological batch state against Odoo stock state at any time.

## 3. Business divisions

### 3.1 Duck farming (Slice 1 — active)
- Flock lifecycle: DOD/pullet receipt → placement → growth/laying → end-of-cycle
- Daily operations: feed consumption, water, health observations
- Outputs: eggs (daily collection), meat (end-of-cycle harvest), manure (continuous byproduct)
- Mortality tracking with mandatory stock write-off sync
- Shed/pen as physical hierarchy

### 3.2 Hydroponic (Slice 2 — deferred)
- Seeds, nursery, nutrient preparation, crop cycle, harvest, grading, packing

### 3.3 Aquaculture (Slice 3 — deferred)
- PL stocking, feed, pond cycle, water quality, mortality, harvest

### 3.4 Circular economy (Slice 4 — deferred)
- Compost, liquid nutrient processing, vermiculture, worm processing into wormmeal
- Duck manure is the first circular input (captured in Slice 1 as standard inventory, routed in Slice 4)

## 4. Biological modeling rule
Biological growth is not tracked as continuously exact live stock in standard Odoo inventory.
Operational truth during active growth is stored in custom biological models.

Standard Odoo stock/MRP postings happen only at lifecycle gates:
- **Input gate:** DOD/pullet receipt into standard stock, then transfer to flock batch
- **Consumption gate:** Feed/vaccine stock reduction linked to active flock
- **Mortality gate:** Dead bird count in flock batch → stock write-off in Odoo (same transaction)
- **Output gate — eggs:** Daily egg collection → finished goods receipt in Odoo
- **Output gate — meat:** End-of-cycle harvest → finished goods receipt in Odoo
- **Byproduct gate:** Manure capture → standard inventory receipt (storable product, lot-tracked)
- **Scrap/reject:** Condemned birds or rejected output → standard scrap posting

## 5. Duck operations — detailed flow

### 5.1 Flock batch lifecycle
```
DOD/Pullet Purchase → Goods Receipt (standard stock)
    → Flock Batch Creation (custom model)
    → Placement in Duck House/Pen
    → Growth/Laying Phase (daily ops in custom model)
        ├── Daily feed consumption (stock gate)
        ├── Daily egg collection (output gate)
        ├── Mortality events (mortality gate + stock write-off)
        ├── Health observations (custom model log)
        └── Manure capture (byproduct gate)
    → End-of-Cycle Decision
        ├── Meat harvest (output gate)
        └── Flock batch close
```

### 5.2 Flock batch states
- `draft` — batch created, not yet placed
- `placed` — birds in duck house, active operations begin
- `laying` — egg production phase (layer flocks)
- `finishing` — meat finishing phase (broiler flocks)
- `harvesting` — end-of-cycle harvest in progress
- `closed` — batch complete, all gates posted, reconciled
- `cancelled` — batch cancelled before placement

### 5.3 Key fields on flock batch
- `name` — batch reference
- `batch_type` — layer / broiler / breeder
- `division_id` → Duck division
- `site_id` → Farm site
- `zone_id` → Duck house / pen
- `start_date` / `end_date`
- `initial_head_count` — birds placed
- `current_head_count` — computed (initial - cumulative mortality)
- `cumulative_mortality` — sum of mortality events
- `cumulative_eggs` — sum of egg collection events (layers only)
- `state`
- `last_gate_sync` — timestamp of last lifecycle gate posting
- `odoo_stock_state` — JSON snapshot of relevant stock.quant values at last sync

### 5.4 Mortality sync — critical design
When a mortality event is recorded:
1. User enters: date, quantity, cause (disease, predator, heat_stress, unknown, other), notes
2. System creates `agri.flock.mortality` record linked to flock batch
3. **In the same transaction**, system creates a stock write-off:
   - `stock.move` from flock's virtual location → scrap location
   - Product = the live bird product for this flock
   - Quantity = mortality count
   - Lot = flock batch lot
4. Flock batch `current_head_count` is recomputed
5. `last_gate_sync` is updated

If the stock write-off fails, the entire transaction rolls back. No mortality without stock sync.

### 5.5 Feed consumption gate
- User records daily feed consumption per flock batch
- System creates `stock.move` reducing feed product from warehouse → production consumption
- Feed cost accumulates in the biological model for reporting (not auto-posted to WIP journal)

### 5.6 Egg collection gate
- User records daily egg count, grade (if applicable), collection date
- System creates `stock.move` receiving eggs into finished goods
- Product = egg product (with UoM: pieces or trays)
- Lot = generated from flock batch + date

### 5.7 Manure capture
- User records estimated manure output (kg) periodically
- System creates `stock.move` receiving manure into byproduct inventory
- Product = duck manure (storable, lot-tracked)
- No routing to circular processing yet — that waits for Slice 4

## 6. Procurement scope (Slice 1 minimal)
For duck operations, procurement starts simple:
- Purchase orders for DOD/pullets, feed, vaccines, supplements
- Goods receipt with lot assignment
- Vendor bill linkage
- Standard Odoo `purchase` + `purchase_stock` modules — no custom extension yet

Full procurement extension (RFI, RFQ, vendor qualification, comparison) deferred to later slice.

## 7. Finance scope (Slice 1 minimal)
- Standard Indonesian CoA via `l10n_id`
- 5 additional accounts for duck operations (WIP, finished goods, byproduct, loss)
- Manual journal entries for monthly WIP posting
- Batch cost summary report (read-only) to support manual JE preparation
- No automated WIP valuation engine
- No subledger sync
- Vendor bills from procurement flow normally through standard AP

Full finance extension (landed costs, assets, budgeting, analytic dimensions) deferred.

## 8. Coretax scope (deferred)
Not in scope for Slice 1. Tax uses standard `l10n_id` tax configuration.
Coretax connector architecture will be designed when finance extension begins.

## 9. IoT scope (deferred)
Not in scope for Slice 1. Duck house environmental observations are entered manually.
IoT architecture will be designed when operational volume justifies sensor investment.

## 10. Standard Odoo modules — Slice 1

### Install immediately
- `base`
- `mail`
- `stock` (inventory)
- `purchase`
- `purchase_stock`
- `sale_management`
- `account` (with `l10n_id` chart)
- `stock_account`

### Install when needed (not Slice 1)
- `mrp` — when production orders are needed (possibly Slice 2)
- `quality` — when QC workflows are formalized
- `account_accountant` — when advanced accounting features needed
- `analytic` — when cost center tracking begins
- `account_asset` — when fixed asset tracking needed
- `maintenance` — when equipment maintenance tracking needed
- `website_sale` — when e-commerce is relevant

## 11. Custom addons — Slice 1

### Foundation (build first)
- `agri_base_masterdata` — division/site/zone hierarchy, security groups, shared master data
- `agri_biological_batches` — generic biological batch framework (base class)

### Duck operations (build second)
- `agri_duck_ops` — flock batch, mortality, feed, eggs, manure, lifecycle gates

### Deferred addons (not built in Slice 1)
- `agri_hydroponic_ops`
- `agri_aquaculture_ops`
- `agri_packhouse`
- `agri_quality_extension`
- `agri_procurement_extension`
- `agri_finance_extension`
- `agri_circular_economy`
- `agri_coretax_connector`
- `agri_iot_base`
- `agri_sensor_gateway_api`
- `agri_environment_monitoring`
- `agri_water_quality_monitoring`
- `agri_traceability_portal`
- `agri_qr_labels`
- `agri_kpi_dashboard`
- `agri_sustainability_reporting`
- `agri_wip_valuation` — only after 3+ production cycles and manual close experience

## 12. Build strategy — revised

### Slice 1: Duck Farming (current)
- Environment bootstrap
- Standard modules + l10n_id
- Master data hierarchy
- Flock batch lifecycle with all gates
- Manual financial close
- Reconciliation validation

**Exit criteria for Slice 1:**
- [ ] Can receive DOD into stock and create flock batch
- [ ] Can record daily feed consumption with stock reduction
- [ ] Can record mortality with synchronized stock write-off
- [ ] Can collect eggs into finished goods
- [ ] Can capture manure into byproduct inventory
- [ ] Can close flock batch at end of cycle
- [ ] Flock head count matches Odoo stock at all times
- [ ] Finance can prepare manual WIP journal entry from batch cost summary
- [ ] At least one full flock cycle tested end-to-end

### Slice 2: Hydroponic Melon (after Slice 1 validated)
- Crop batch logic
- Harvest/grading/packing
- Greenhouse-specific gates
- Procurement extension if needed

### Slice 3: Aquaculture (after Slice 2 validated)
- Pond batch logic
- Water quality observations
- Harvest logic

### Slice 4: Circular Economy (after Slice 3 or when manure accumulation demands it)
- Compost route
- Vermiculture route
- Worm processing route
- Internal reuse linkage

### Slice 5: Finance & Compliance Hardening
- WIP valuation engine (if justified by volume)
- Coretax connector
- Advanced analytics

### Slice 6: IoT & Reporting
- IoT base + sensor gateway
- Environment monitoring
- KPI dashboard
- Sustainability reporting

## 13. Technical success criteria — Slice 1
The duck slice is successful when:
- Flock batch tracks birds from receipt to end-of-cycle
- Every gate posting creates correct `stock.move` records
- Mortality never creates shadow ledger drift
- Feed consumption reduces stock accurately
- Egg and meat output appears in finished goods
- Manure is captured as lot-tracked inventory
- Finance can close the month with manual JEs
- Batch cost summary report is accurate and useful
- Security groups control access appropriately
- Addon installs and upgrades cleanly
