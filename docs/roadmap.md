# roadmap.md
# Gaialangit ERP — Scaling Roadmap
## From Duck Farming to Full Integrated Operations

---

## Roadmap Philosophy

Each slice follows the same pattern:
1. **Scaffold** — addon structure, models, security
2. **Gates** — lifecycle gate postings with stock sync
3. **Reconcile** — verify biological model matches Odoo stock
4. **Harden** — simulate full cycle, manual financial close, fix issues
5. **Decide** — only then choose the next slice

No slice begins until the previous slice's hardening phase passes.
No automation is built until manual processes are proven painful.

---

## Milestone 0: Environment Bootstrap
**Goal:** Reproducible local dev environment with pinned Odoo version.

| Task | Deliverable | Done? |
|------|-------------|-------|
| Smoke-test Odoo 19 nightly | Version decision documented | ☐ |
| Create docker-compose.yml | Odoo + PG16 wired | ☐ |
| Create config/odoo.conf | Addon path mounted | ☐ |
| Create all scripts | setup, start, stop, init_db, install, upgrade | ☐ |
| Create .env.example | Pinned version slot | ☐ |
| Create README.md | Local setup instructions | ☐ |
| Validate Odoo starts | Login page visible | ☐ |
| Create empty DB via CLI | DB exists, no errors | ☐ |

**Exit gate:** `./scripts/start_odoo.sh` brings up a working Odoo instance.

---

## Milestone 1: Standard Foundation
**Goal:** Core Odoo modules installed with Indonesian localization.

| Task | Deliverable | Done? |
|------|-------------|-------|
| Install stock, purchase, purchase_stock | Modules active | ☐ |
| Install sale_management | Module active | ☐ |
| Install account + l10n_id | Indonesian CoA loaded | ☐ |
| Install stock_account | Inventory valuation active | ☐ |
| Create company record | Gaialangit company configured | ☐ |
| Configure warehouse | Main warehouse with locations | ☐ |
| Add 5 duck CoA accounts | WIP, FG eggs, FG meat, byproduct, loss | ☐ |
| Create duck products | DOD, feeds, vaccine, live duck, eggs, meat, manure | ☐ |
| Design security groups | 4 groups documented with CRUD matrix | ☐ |

**Exit gate:** Can create a purchase order for duck feed and receive it into stock.

---

## Milestone 2: Master Data Addon
**Goal:** Physical hierarchy and security groups in a custom addon.

| Task | Deliverable | Done? |
|------|-------------|-------|
| Scaffold agri_base_masterdata | __manifest__, models, views, security | ☐ |
| Division model | CRUD works in UI | ☐ |
| Site model | Linked to division, CRUD works | ☐ |
| Zone model | Linked to site, zone_type field, CRUD works | ☐ |
| Security groups | 4 groups in security.xml | ☐ |
| Access rules | ir.model.access.csv complete | ☐ |
| Menus | Farming top menu with sub-menus | ☐ |
| Install validation | `install_addon.sh agri_base_masterdata` succeeds | ☐ |

**Exit gate:** Can create Duck Division → Farm Site → Duck House Zone in UI.

---

## Milestone 3: Biological Batch Framework
**Goal:** Generic batch base class that duck (and later hydro/aqua) extends.

| Task | Deliverable | Done? |
|------|-------------|-------|
| Scaffold agri_biological_batches | Addon structure complete | ☐ |
| Base batch model | Core fields + state machine | ☐ |
| Anti-drift fields | last_gate_sync, odoo_stock_state | ☐ |
| Base views | Form + tree | ☐ |
| Security | Access rules per group | ☐ |
| Install validation | Addon installs cleanly | ☐ |

**Exit gate:** Base biological batch model exists and can be extended.

---

## Milestone 4: Duck Operations — Gates
**Goal:** Complete flock lifecycle with all stock-synced gate postings.

### 4A. Flock Batch + Input Gate
| Task | Deliverable | Done? |
|------|-------------|-------|
| Flock batch model (extends base) | Duck-specific fields + states | ☐ |
| Input gate logic | DOD receipt → flock batch creation → stock transfer | ☐ |
| UI | Flock batch form with create-from-receipt flow | ☐ |
| Validation | Create flock, verify stock.quant shows birds | ☐ |

### 4B. Feed Consumption Gate
| Task | Deliverable | Done? |
|------|-------------|-------|
| Feed log model | batch, date, product, qty fields | ☐ |
| Stock move on confirm | Feed reduced from warehouse | ☐ |
| UI | Feed log form within flock batch | ☐ |
| Validation | Record feed, verify stock.quant decreases | ☐ |

### 4C. Mortality Gate (Critical)
| Task | Deliverable | Done? |
|------|-------------|-------|
| Mortality model | batch, date, qty, cause fields | ☐ |
| Transactional stock write-off | Same-transaction stock.move to scrap | ☐ |
| Head count recompute | current_head_count updates | ☐ |
| Anti-drift sync | last_gate_sync updates | ☐ |
| Rollback test | Verify failed stock move rolls back mortality | ☐ |
| UI | Mortality form with cause selection | ☐ |
| Validation | Record mortality, verify stock matches head count | ☐ |

### 4D. Egg Collection Gate
| Task | Deliverable | Done? |
|------|-------------|-------|
| Egg collection model | batch, date, qty, grade fields | ☐ |
| Stock move on confirm | Eggs into finished goods | ☐ |
| Lot generation | batch_ref + date format | ☐ |
| UI | Egg collection form | ☐ |
| Validation | Collect eggs, verify FG stock increases | ☐ |

### 4E. Meat Harvest Gate
| Task | Deliverable | Done? |
|------|-------------|-------|
| End-of-cycle workflow | Harvest action on flock batch | ☐ |
| Stock move | Meat into finished goods | ☐ |
| Batch close | State → closed after harvest | ☐ |
| Validation | Harvest, verify FG stock, verify batch closed | ☐ |

### 4F. Manure Capture Gate
| Task | Deliverable | Done? |
|------|-------------|-------|
| Manure log model | batch, date, estimated_kg fields | ☐ |
| Stock move on confirm | Manure into byproduct location | ☐ |
| Lot tracking | Lot assigned for future circular linkage | ☐ |
| Validation | Capture manure, verify byproduct stock | ☐ |

### 4G. Reporting & Reconciliation
| Task | Deliverable | Done? |
|------|-------------|-------|
| Batch cost summary report | Read-only per-batch cost breakdown | ☐ |
| Reconciliation check | Compare flock model vs Odoo stock | ☐ |
| Discrepancy flagging | Highlight any mismatch | ☐ |
| Validation | Run reconciliation on test data, verify accuracy | ☐ |

**Exit gate:** All 7 gate types create correct stock.move records.
Reconciliation check passes on a multi-day simulated flock.

---

## Milestone 5: Financial Hardening Pause
**Goal:** Prove the duck system works for real financial operations.

| Task | Deliverable | Done? |
|------|-------------|-------|
| Simulate full layer flock cycle | 60-day cycle with daily ops | ☐ |
| Simulate full broiler flock cycle | 45-day cycle with daily ops | ☐ |
| Run reconciliation check | All counts match | ☐ |
| Manual WIP journal entry | Finance creates JE from cost summary | ☐ |
| Document month-end procedure | Step-by-step guide for Finance | ☐ |
| Identify and fix UX issues | Issues logged and resolved | ☐ |
| Security group verification | Each role can only do what it should | ☐ |

**Exit gate:** Finance confirms they can close a month.
At least one full flock cycle passes all checks.

---

## Milestone 6: Second Slice Decision
**Goal:** Choose and validate the next division to implement.

| Factor | Hydroponic | Aquaculture |
|--------|------------|-------------|
| Revenue urgency | ? | ? |
| Operational complexity | Medium | High |
| Circular economy linkage | Medium (biomass) | Medium (sludge) |
| Shared patterns with duck | Medium | High |

Decision made by business team after Milestone 5 completes.
Same pattern applies: scaffold → gates → reconcile → harden → decide.

---

## Milestone 7–8: Second & Third Division
Repeat the Milestone 2–5 pattern for the chosen division.
Each division adds:
- Division-specific batch model (extends biological batch base)
- Division-specific gate postings
- Division-specific products and CoA accounts (incremental)
- Division-specific reconciliation checks
- Manual financial close validation

---

## Milestone 9: Circular Economy
**Goal:** Route accumulated byproducts into processing.

**Prerequisites:**
- Duck manure already in standard inventory (from Slice 1)
- At least one other byproduct source available
- Business has defined which circular routes to activate first

| Task | Deliverable |
|------|-------------|
| Scaffold agri_circular_economy | Addon structure |
| Feedstock acceptance gate | QC screening, release to processing |
| Compost batch logic | Process tracking, output gate |
| Vermiculture batch logic | Worm growth, output gate (vermicompost + biomass) |
| Worm processing route | Wormmeal output with release states |
| Internal reuse linkage | Circular output → division input |
| Reconciliation | Circular stock matches process records |

---

## Milestone 10: Procurement & Finance Extensions
**Goal:** Advanced procurement and financial automation.

**Prerequisites:**
- At least 2 divisions operational
- 3+ manual month-end closes completed
- Finance has validated CoA and cost flow patterns

| Task | Deliverable |
|------|-------------|
| agri_procurement_extension | RFI, RFQ, vendor qualification, comparison |
| agri_finance_extension | Analytic dimensions, landed costs, budgeting |
| agri_wip_valuation (if justified) | Daily roll-up, EOM wizard, discrepancy review |

**Decision criteria for WIP valuation engine:**
- Are manual JEs taking > 2 hours per month-end?
- Are there > 50 active batches across divisions?
- Has Finance requested automation?
If no to all three → continue manual.

---

## Milestone 11: IoT Integration
**Goal:** Automated environmental monitoring.

**Prerequisites:**
- Sensor hardware deployed at duck house (or greenhouse/pond)
- Middleware and time-series store selected and running
- Alert thresholds defined by operations team

| Task | Deliverable |
|------|-------------|
| agri_iot_base | Device registry, threshold config, alert model |
| agri_sensor_gateway_api | REST endpoint for middleware → Odoo events |
| agri_environment_monitoring | Duck house / greenhouse monitoring views |
| agri_water_quality_monitoring | Aquaculture water quality (if Slice 3 done) |

---

## Milestone 12: Compliance & Reporting
**Goal:** Tax compliance and operational dashboards.

| Task | Deliverable |
|------|-------------|
| agri_coretax_connector | Tax mapping, submission log, audit trail |
| agri_kpi_dashboard | Operational KPIs per division |
| agri_sustainability_reporting | Circular economy metrics, waste reduction |
| agri_traceability_portal | End-to-end lot trace (supplier → customer) |
| agri_qr_labels | QR code generation for lot tracking |

---

## Scaling Timeline (Indicative)

```
Month 1-2:    Milestone 0-1  (Environment + Standard Foundation)
Month 2-3:    Milestone 2-3  (Master Data + Batch Framework)
Month 3-5:    Milestone 4    (Duck Gates — all 7 types)
Month 5-6:    Milestone 5    (Financial Hardening — full cycle test)
              ── FIRST PRODUCTION DEPLOYMENT (Duck only) ──
Month 6-8:    Milestone 6-7  (Second Division)
Month 8-10:   Milestone 8    (Third Division)
Month 10-12:  Milestone 9    (Circular Economy)
Month 12-14:  Milestone 10   (Procurement & Finance Extensions)
Month 14-16:  Milestone 11   (IoT)
Month 16-18:  Milestone 12   (Compliance & Reporting)
```

**These are estimates.** Actual timing depends on:
- Odoo version stability
- Business team availability for testing
- Operational volume growth
- How quickly manual processes become painful enough to justify automation

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Dangerous | What to Do Instead |
|---|---|---|
| Building all addons at once | Untestable, fragile interdependencies | One addon at a time, install-test-proceed |
| Automating WIP valuation early | No real data to validate against | Manual JEs first, automate when proven |
| Designing 40+ CoA accounts upfront | Most will be wrong or unused | Add 3-5 accounts per slice |
| Building IoT before operations work | Sensor data has no consumer | Manual entry until ops are stable |
| Designing Coretax before accounting works | Tax mapping needs real transactions | Use l10n_id standard taxes first |
| Skipping reconciliation checks | Shadow ledger drift goes undetected | Reconcile after every gate implementation |
| Building OWL components in MVP | Complex frontend for unproven UX | Smart buttons + standard views first |
| Multiple addons in one session | Scope creep, untested interactions | One bounded task per session |

---

## Success Metrics by Phase

### After Slice 1 (Duck)
- Zero discrepancy between flock count and Odoo stock
- Finance can close month in < 1 hour with manual JEs
- Farm operators use the system daily without support calls

### After Slice 2-3 (Second + Third Division)
- Biological batch pattern proven reusable across divisions
- CoA growth is incremental and clean
- No breaking changes to existing slices when new ones are added

### After Slice 4 (Circular Economy)
- Byproducts flow from division inventory into circular processing
- Circular outputs are traceable back to source batches
- Internal reuse reduces external input costs (measurable)

### After Full System
- End-to-end traceability from supplier to customer
- Monthly financial close < 2 hours (manual or automated)
- Tax compliance ready for Coretax submission
- IoT alerts trigger actionable Odoo events
- KPI dashboard shows operational health across all divisions
