# Manual Month-End Close Procedure — Duck Operations
**Version:** 1.0 (Phase 4, 2026-04-02)
**Status:** Tested on simulated flock cycle BATCH-SIM-2026-003

---

## Overview

This document describes the manual month-end close for duck operations under the
**manual-first accounting rule** (CLAUDE.md). No automated WIP valuation engine
is used. Finance posts WIP journal entries manually using batch cost summary reports.

---

## Prerequisites

Before month-end close:
- All flock batches have been reconciliation-checked (no discrepancies)
- All gate logs for the period are confirmed (no draft feed/mortality/egg logs)
- Standard Odoo stock valuation is up to date

---

## Step 1: Run Reconciliation Check on All Active Batches

For each active flock batch:
1. Go to **Farming → Duck Operations → Flock Batches**
2. Open each batch in `Placed` / `Laying` / `Finishing` / `Harvesting` state
3. Click **Check Reconciliation**
4. If it passes: proceed
5. If it fails: investigate and fix gate log discrepancies before closing the period

---

## Step 2: Print Batch Cost Summary Reports

For each batch (active or closed-this-period):
1. From the flock batch form, click **Print → Batch Cost Summary**
2. The report shows:
   - **DOD Cost**: `initial_count × live_bird_product.standard_price`
   - **Feed Cost**: sum of confirmed feed logs × feed product standard_price (approximation — use actual PO lines for final)
   - **Mortality Loss**: deceased count × live_bird_product.standard_price
   - **Egg output**: cumulative_eggs collected
   - **Harvest output**: total birds harvested, total meat kg
   - **Manure output**: total kg captured
3. **Note:** The report prominently states "No auto-posting. Use this to prepare manual WIP JEs." Standard prices are approximations — cross-reference actual PO lines for accurate costs.

---

## Step 3: Calculate WIP Value (Closing Balance)

For each active batch at month-end:

```
WIP Balance (closing) =
    DOD Cost (initial stock × purchase price)
  + Feed Cost (actual PO line costs for the period)
  - Mortality Loss (deceased × cost per bird)
  - Egg Revenue-equivalent (optional — depends on CoA design)
  - Harvested birds (removed from WIP into FG)
```

Cross-reference:
- Purchase orders for DOD/feed (actual purchase cost)
- Stock valuation report for live birds (to verify stock)
- Batch Cost Summary for operational totals

---

## Step 4: Post Manual WIP Journal Entries

Post in Odoo Accounting → Journal Entries → New:

### 4a. WIP Accrual (for active batches)

| Account | Debit | Credit |
|---------|-------|--------|
| Biological WIP — Duck (Balance Sheet) | WIP increase for period | |
| Feed Expense / COGS | | Feed cost for period |
| DOD Expense / Purchase Clearing | | DOD cost for period |

### 4b. Mortality Write-Off

| Account | Debit | Credit |
|---------|-------|--------|
| Abnormal Loss — Duck (P&L Expense) | Mortality loss value | |
| Biological WIP — Duck | | Mortality loss value |

### 4c. Egg Output (when eggs are sold or transferred to FG)

| Account | Debit | Credit |
|---------|-------|--------|
| Inventory — Duck Eggs (Balance Sheet) | Egg inventory value | |
| Biological WIP — Duck | | Egg production cost allocated |

### 4d. Meat Harvest Output

| Account | Debit | Credit |
|---------|-------|--------|
| Inventory — Duck Meat (Balance Sheet) | Meat inventory value | |
| Biological WIP — Duck | | Harvested bird cost allocated |

### 4e. Manure Byproduct

| Account | Debit | Credit |
|---------|-------|--------|
| Inventory — Duck Manure (Balance Sheet) | Manure value | |
| Biological WIP — Duck | | Manure production cost allocated |

---

## Step 5: Reconcile WIP Account Balance

After posting:
1. Run trial balance (Accounting → Reporting → Trial Balance)
2. Check "Biological WIP — Duck" account balance
3. Expected: balance represents total cost of birds still in active production
4. Cross-check against sum of all active batch `total_dod_cost + total_feed_cost - total_mortality_loss`

---

## Step 6: Document and Archive

1. Save printed Batch Cost Summary PDFs for each batch
2. Note journal entry references on the batch form (use chatter/notes field)
3. File under the closing month folder

---

## Known Limitations (Phase 4)

1. **Standard prices are approximations.** `total_feed_cost` uses `product.standard_price`
   not actual PO line prices. Finance must manually adjust using actual PO costs.

2. **No cost allocation engine.** Egg/meat/manure cost allocation is manual.
   A simple method: allocate WIP in proportion to output kg/units.

3. **Negative production location quants.** Output moves (Production → WH/Stock) create
   negative quants at the Production virtual location. This is expected Odoo behavior
   for production-sourced outputs. Total stock value remains correct.

4. **No sub-ledger.** All WIP is aggregated into one account. Batch-level P&L is only
   available via the Batch Cost Summary report, not from the GL directly.

5. **Manual egg cost allocation.** No standard cost is set for egg output cost.
   Finance should determine allocation method (e.g., % of total feed cost).

---

## Trigger: When to Automate

Automate the WIP valuation engine after:
- 3+ full production cycles completed with real data
- 2+ month-end closes performed manually
- Finance validates CoA mapping against actual transactions

Until then: **manual-first, always**.
