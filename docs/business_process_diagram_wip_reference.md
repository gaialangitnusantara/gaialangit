┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                         GAIALANGIT INTEGRATED FARMING ERP - FINAL BUSINESS FLOW                   │
│                                      (Aligned with Odoo PRD)                                      │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘

A. ENTERPRISE FOUNDATION
──────────────────────────────────────────────────────────────────────────────────────────────────────
Company / Divisions / Sites / Warehouses / Locations / Products / UoM / Lots / Analytic Dimensions
        │
        ▼
Standard Odoo Foundation
- Inventory
- Purchase
- MRP
- Quality
- Sales
- Accounting
- Analytic / Assets / Maintenance / Approvals

══════════════════════════════════════════════════════════════════════════════════════════════════════

B. SOURCE-TO-PAY (PROCUREMENT TO RECEIPT TO BILL)
──────────────────────────────────────────────────────────────────────────────────────────────────────
Operational Need / Replenishment Trigger
        │
        ▼
Vendor Qualification / Vendor Master
        │
        ├── RFI (technical/compliance information request)
        │
        ├── RFQ (commercial quotation request)
        │
        ├── Quotation Comparison / Vendor Selection
        │
        └── Approved Purchase Order
                 │
                 ▼
         Goods Receipt / Incoming QC / Lot Assignment
                 │
                 ├── Accepted to Raw Material Inventory
                 ├── Rejected / Return to Vendor
                 └── Hold / Quarantine
                 │
                 ▼
             Vendor Bill
                 │
                 ▼
        Payment / Reconciliation / Cost Allocation

══════════════════════════════════════════════════════════════════════════════════════════════════════

C. RAW MATERIAL INVENTORY
──────────────────────────────────────────────────────────────────────────────────────────────────────
Raw Material Inventory (official stock ledger)
        │
        ├── Hydro inputs
        │   - seeds
        │   - nutrients
        │   - media
        │   - packaging
        │
        ├── Aquaculture inputs
        │   - PL / juveniles
        │   - feed
        │   - additives
        │
        ├── Duck inputs
        │   - ducklings
        │   - feed
        │   - meds / supplements
        │
        └── Shared inputs
            - utilities
            - tools
            - maintenance parts
            - process consumables

══════════════════════════════════════════════════════════════════════════════════════════════════════

D. BIOLOGICAL OPERATIONS (CUSTOM OPERATIONAL TRUTH / WIP)
──────────────────────────────────────────────────────────────────────────────────────────────────────
NOTE:
During active biological growth, operational truth lives in custom biological models.
Standard Odoo stock is updated only at lifecycle gates.

        ┌────────────────────────────┬──────────────────────────────┬───────────────────────────────┐
        │                            │                              │                               │
        ▼                            ▼                              ▼                               ▼

   D1. HYDROPONIC                D2. AQUACULTURE                D3. DUCK FARMING              D4. SHARED OPS
   Crop Batch WIP                Pond Batch WIP                 Flock Batch WIP               Maintenance / Utilities
        │                            │                              │
        ├── seed/nursery stage       ├── stocking stage             ├── placement stage
        ├── transplant stage         ├── grow-out stage             ├── growth/layer stage
        ├── nutrient cycle           ├── feeding cycle              ├── feed/water cycle
        ├── climate observations     ├── mortality logs             ├── health observations
        ├── crop observations        ├── pond observations          ├── mortality logs
        └── operational logs         └── operational logs           └── yield observations

══════════════════════════════════════════════════════════════════════════════════════════════════════

E. OPERATIONAL IOT TELEMETRY (NOT RAW ERP TRANSACTION STORAGE)
──────────────────────────────────────────────────────────────────────────────────────────────────────
Sensors / Devices
        │
        ▼
Gateway / Middleware / Time-Series Layer
        │
        ▼
Odoo Receives Only:
- device registry
- last summarized state
- threshold breach
- alert event
- maintenance / quality trigger
- link to site / zone / pond / tank / house / batch / process

Telemetry domains:
- greenhouse temperature / RH / DLI / light / EC / pH / water temp / tank level
- aquaculture temperature / pH / DO / salinity / ammonia / ORP / turbidity / water level
- duck house temperature / humidity / airflow / feed-water status
- circular process temperature / moisture / pH / tank level / condition markers

        │
        ▼
Operational Alerts
        ├── Activity
        ├── Quality Alert
        ├── Maintenance Ticket
        └── Supervisor Escalation

══════════════════════════════════════════════════════════════════════════════════════════════════════

F. LIFECYCLE GATES (OFFICIAL ODOO POSTINGS)
──────────────────────────────────────────────────────────────────────────────────────────────────────
Biological WIP / Operational Events
        │
        ▼
Lifecycle Gate Posting
        │
        ├── Input issue
        ├── Controlled stage transfer
        ├── Harvest recognition
        ├── Mortality / loss posting
        ├── Scrap / reject posting
        ├── Output recognition
        └── Byproduct capture

        │
        ▼
Official Odoo Stock / MRP / Costing Impact

══════════════════════════════════════════════════════════════════════════════════════════════════════

G. PRIMARY OUTPUT STREAMS
──────────────────────────────────────────────────────────────────────────────────────────────────────
        ┌────────────────────────────┬──────────────────────────────┬───────────────────────────────┐
        │                            │                              │                               │
        ▼                            ▼                              ▼                               ▼
   Melon Harvest Lots             Shrimp Harvest Lots             Duck Outputs                    Byproduct Lots
        │                            │                              │                               │
        │                            │                              ├── egg / meat output          ├── duck manure
        │                            │                              └── manure capture             ├── aqua sludge
        │                            │                                                              ├── melon biomass
        │                            │                                                              └── selected domestic organic waste
        ▼
Packhouse / Grading / Packing
        │
        ├── Premium Grade
        ├── Secondary Grade
        ├── Reject / Circular biomass
        └── Packed Commercial Lots

══════════════════════════════════════════════════════════════════════════════════════════════════════

H. CIRCULAR ECONOMY SUB-SYSTEM
──────────────────────────────────────────────────────────────────────────────────────────────────────
Circular Input Pool
- duck manure
- aquaculture sludge
- melon biomass
- selected domestic organic waste
- bulking agents
- additives / microbial support
        │
        ▼
Feedstock Acceptance Gate
        │
        ├── contamination screening
        ├── segregation approval
        ├── suitability check
        └── release to circular processing
        │
        ▼
Pre-Processing / Sorting / Mixing
        │
        ├───────────────────────────────┬───────────────────────────────┬───────────────────────────────┐
        │                               │                               │                               │
        ▼                               ▼                               ▼                               ▼

   H1. Compost Route               H2. Liquid Nutrient Route       H3. Vermiculture Route         H4. Other Circular
        │                               │                               │                               │
        ▼                               ▼                               ▼
   Compost Batch                    Liquid Process Batch            Vermiculture Batch
                                                                            │
                                                                            ├── worm growth
                                                                            ├── organic conversion
                                                                            ├── moisture / pH / temp checks
                                                                            └── batch condition logs
                                                                            │
                                                                            ▼
                                                                   Vermiculture Output Gate
                                                                            │
                                                                            ├── Vermicompost Lot
                                                                            ├── Worm Biomass Lot
                                                                            └── Reject / Loss Lot
                                                                                    │
                                                                                    ▼
                                                                           Worm Processing Route
                                                                                    │
                                                                                    ▼
                                                                           Worm Processing Batch
                                                                                    │
                                                                                    ▼
                                                                           Worm Processing Output Gate
                                                                                    │
                                                                                    ├── Wormmeal Lot
                                                                                    └── Reject / Loss Lot

══════════════════════════════════════════════════════════════════════════════════════════════════════

I. QUALITY AND RELEASE CONTROL
──────────────────────────────────────────────────────────────────────────────────────────────────────
Quality Control Points exist across:
- incoming materials
- biological observations
- harvest
- grading / packhouse
- circular inputs
- circular outputs
- wormmeal release
        │
        ▼
Release State
- hold
- pass
- conditional
- reject
- experimental
- internal_trial
- approved_for_internal_use
- approved_for_feed
- approved_for_sale

══════════════════════════════════════════════════════════════════════════════════════════════════════

J. INTERNAL REUSE AND INTER-DIVISION FLOWS
──────────────────────────────────────────────────────────────────────────────────────────────────────
Released Circular Outputs
        │
        ├── Compost -> internal reuse / external sale
        ├── Liquid nutrient -> hydroponic input support
        ├── Vermicompost -> internal soil / circular use / sale
        ├── Worm biomass -> trial / further processing
        └── Wormmeal -> internal trial / approved feed use / sale
        │
        ▼
Internal Transfer / Consumption Posting
        │
        ▼
Division-Level Costing / Sustainability Tracking

══════════════════════════════════════════════════════════════════════════════════════════════════════

K. ORDER-TO-CASH
──────────────────────────────────────────────────────────────────────────────────────────────────────
Commercial Output Available
        │
        ├── B2B Bulk Sales
        │   - shrimp
        │   - ducks
        │   - circular products
        │
        └── Premium Retail / B2B Premium
            - branded melons
        │
        ▼
Sales Order
        │
        ▼
Delivery / Lot Traceability / Customer Fulfilment
        │
        ▼
Customer Invoice
        │
        ▼
Payment
        │
        ▼
Reconciliation

══════════════════════════════════════════════════════════════════════════════════════════════════════

L. RECORD-TO-REPORT
──────────────────────────────────────────────────────────────────────────────────────────────────────
Procurement + Inventory + Production + Sales + Finance
        │
        ▼
Accounting Ledger
- journals
- taxes
- AP / AR
- analytic dimensions
- landed cost
- assets where applicable
        │
        ▼
Coretax Connector Layer
- tax mapping
- submission log
- exception handling
        │
        ▼
Financial Reporting / KPI / Sustainability Reporting

══════════════════════════════════════════════════════════════════════════════════════════════════════

M. TRACEABILITY LAYER
──────────────────────────────────────────────────────────────────────────────────────────────────────
End-to-end traceability must be available across:
- supplier / PO / receipt
- input lot
- biological batch
- lifecycle gate posting
- harvest lot
- grading lot
- packed lot
- byproduct lot
- circular process batch
- vermicompost lot
- worm biomass lot
- wormmeal lot
- sale / invoice / customer-facing trace context