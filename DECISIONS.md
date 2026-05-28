# DECISIONS.md — Every Ambiguity Resolved

> **For each decision: what the ambiguity was, what we chose, why, and what we'd ask the PM
> if given one conversation.**

---

## Decision 1 — Multi-tenancy implementation strategy

### The Ambiguity
The spec said "multi-tenant" but didn't say how. Three valid approaches existed:
1. **Separate database per tenant** — maximum isolation, maximum ops complexity
2. **Schema-per-tenant** — good isolation, complex migrations (requires `django-tenants` or similar)
3. **Shared schema with row-level FK** — simplest ops, requires disciplined queryset filtering

### What We Chose
Shared schema with a `TenantModel` abstract base class that stamps `organisation FK` on every
business data model. Enforcement is at three levels:
- DB level: non-nullable FK with B-tree index on every table
- ORM level: `get_active_organisation(request)` resolves tenant from JWT on every view
- Test level: every queryset in views is filtered by `organisation=org` before returning data

### Why
At 1–50 tenants with datasets in the hundreds-of-thousands-of-rows range, shared schema is
demonstrably faster to operate and test. The risk (cross-tenant data leakage) is mitigated by
the abstract base class pattern — if you forget to call `filter(organisation=org)` in a view,
the API returns data for the wrong tenant, which is immediately visible in testing.

### What We'd Ask the PM
*"What is the contractual data isolation requirement? Is 'same DB, row-level FK' acceptable to
enterprise clients' InfoSec teams, or do they require dedicated schema/database?"* Most mid-market
ESG SaaS companies (Watershed, Persefoni) use shared schema. But if the customer is a BFSI
company with SEBI data localisation requirements, dedicated schema may be contractually mandatory.

---

## Decision 2 — Scope assignment authority (who decides Scope 1 vs 2 vs 3?)

### The Ambiguity
GHG Protocol draws Scope lines based on organizational boundary and ownership, not just fuel type.
A diesel generator at a company-owned plant is Scope 1. Diesel purchased and delivered to a
third-party logistics partner is Scope 3. The data (a purchase order for diesel) looks identical.

### What We Chose
Scope is assigned by the **parser**, not the user, using three signals in priority order:

1. **`PlantLookup.default_scope`** — the admin pre-configures each SAP WERKS code with its
   default scope. This handles 90% of cases (known plants, known boundary).
2. **`esg_category` keyword matching** — if plant lookup misses, the material description is
   matched against a keyword table (`diesel → SCOPE_1`, `electricity → SCOPE_2`, `flight → SCOPE_3`).
3. **Manual override** — users can change `ghg_scope` on any `PENDING` or `FLAGGED` row.
   This change is audit-logged.

### Subset Handled
- SAP: Only **direct fuel procurement** (PO documents for diesel, petrol, CNG, LPG). Excluded:
  refrigerant purchases, process chemicals, raw materials. These require a separate BOM analysis
  that wasn't in scope.
- Utility: Only **electricity consumption** (Scope 2 — market-based or location-based). Excluded:
  natural gas utility bills (requires separate Scope 1 treatment), district heating, steam.
- Travel: Only **employee business travel** (Scope 3, Category 6 per GHG Protocol). Excluded:
  customer commute, supplier transport (Category 4/9), freight.

### What We'd Ask the PM
*"Is the organizational boundary equity-based (financial control) or operational control? Does
the company include joint ventures? If a diesel purchase is for a vehicle driven by a contractor,
is that Scope 1 or Scope 3?"* These are genuine SEBI BRSR boundary questions that cannot be
answered with code — they require a Board-level policy decision.

---

## Decision 3 — What "editing" a row means and whether it's allowed

### The Ambiguity
Real ESG data has errors. A utility bill gets re-issued. A travel expense gets corrected.
A fuel quantity is transposed. The question is: do you allow in-place edits, or do you
force a re-ingest?

### What We Chose
**No in-place edits to calculation fields.** The following are immutable once set:
- `co2e_kg`, `formula`, `emission_factor_value`, `emission_factor_record_id`
- `AuditLog` records (enforced by `PermissionDenied` in `save()`)
- `RowComment` body (enforced by `PermissionDenied` in `save()`)

**What can change:**
- `status` — via the review workflow (PENDING → FLAGGED → APPROVED → LOCKED)
- `anomaly_flags` — machine can re-flag after re-analysis
- `RowComment.resolved` — findings can be resolved without being erased

**The re-ingest pattern for corrections:**
If a row has wrong data, the correct workflow is:
1. `REJECT` the row (logged to `AuditLog`)
2. Correct the source file
3. Re-upload → new `RawUpload` → new row with correct values

This creates a clear trail: the rejected row explains why, the new row shows the correction.

### What We'd Ask the PM
*"What does your external assurance firm (Big 4 ESG practice) say about in-place corrections?
Do they require the original value plus the corrected value to both be visible, or is a rejection
+ re-ingest with a comment sufficient?"* The answer changes whether we need a `previous_values`
JSON field on `NormalisedRow` (currently absent by design).

---

## Decision 4 — Emission factor versioning (what happens when CEA releases V21?)

### The Ambiguity
India's CEA releases a new grid emission factor database approximately every 12 months. When
the new factor is published, should historical electricity calculations be recomputed, or frozen?

### What We Chose
**Historical calculations are frozen.** The `emission_factor_record_id` on every `UtilityRow`
points to the specific `EmissionFactor` row that was active when the row was ingested. When CEA
publishes V21 (FY 2025-26 factor), we:
1. Add a new `EmissionFactor` row with `valid_from_fy = '2025-26'` and `is_active = True`
2. Set the old row to `is_active = False` (never delete)
3. New ingestion picks up the new factor; old rows keep `emission_factor_record_id` pointing
   to the V20 row

SEBI BRSR requires disclosure to use the factor current at the time of the reporting period,
not the latest available factor. This design is therefore regulation-compliant.

### What We'd Ask the PM
*"If a client wants to retroactively restate their FY 2024-25 figures using the V21 factor
(common in sustainability reports to show year-on-year comparability), do we support that?
It would require a separate 'restated' snapshot table and a recomputation job."*

---

## Decision 5 — India FY vs Calendar Year throughout the system

### The Ambiguity
India's financial year runs April to March. European operations (if any) run January to December.
Which calendar does the system use as the primary temporal axis?

### What We Chose
**India FY is the primary axis for all reporting and forecasting.** Every BRSR report, every
forecast query, every dashboard chart uses India FY strings (`"2025-26"` = Apr 2025 – Mar 2026).

For multi-country operations, raw data retains its original calendar date (`document_date`,
`billing_start`, `travel_date`) and the India FY is computed at query time using:
```
FY_start_year = year if month >= 4 else year - 1
FY_string = f"{FY_start_year}-{str(FY_start_year + 1)[2:]}"
```

### What We'd Ask the PM
*"Are there European or US subsidiaries that need CY reporting? If yes, do they file separate
CSRD or SEC climate disclosures? If so, we need a second reporting calendar layer and the
intensity ratio denominators change significantly."*

---

## Decision 6 — What subset of SAP we handle and what we ignore

### SAP Sources Handled
- **Transaction ME2M** (Purchase Orders by Material): fuel procurement POs
- **Transaction MB51** (Material document list): goods receipts for fuel materials
- **Flat-file export format**: SAP GUI export as tab-separated or semicolon-separated UTF-8/Latin-1

### Fields Used
`EBELN` (PO), `EBELP` (line item), `MATNR` (material), `TXZ01` (description), `WERKS` (plant),
`MENGE` (quantity), `MEINS` (unit), `NETWR` (net value), `WAERS` (currency), `BEDAT` (document date)

### Explicitly Ignored
- **ME21N / ME23N** (PO creation and change transactions) — source of truth is the goods receipt, not the order
- **CO2 claims embedded in SAP GTS** (Global Trade Services) — too company-specific to normalise
- **SAP Sustainability Control Tower (SCT)** — a separate SAP product that outputs its own CO2 figures; ingesting both would create double-counting risk
- **Bill of Materials (BOM) analysis** — required for upstream Scope 3 (Categories 1, 2) but out of scope
- **Asset Master data** (for Scope 1 from owned vehicles) — complex fleet management, deferred

### What We'd Ask the PM
*"Does the client use SAP SCT? If yes, we need to decide whether BreatheESG recomputes from
raw procurement data (our approach) or ingests SCT output. Ingesting SCT output is faster to
implement but means we are auditing their black box, not the source data."*

---

## Decision 7 — Travel data: Navan/Concur API vs receipt-level parsing

### Handled
- **Navan/Concur standard booking export** (CSV format, one row per segment):
  air flights, hotel bookings, car rentals
- IATA codes resolved to lat/lon via `Airport` table (OurAirports dataset)
- Haversine formula for great-circle distance when ICAO table doesn't match
- RFI (Radiative Forcing Index) applied to air segments: `rfi_applied = True`

### Ignored
- **Personal vehicle mileage claims** (expense reports) — not available in booking APIs; requires
  separate mileage reimbursement data feed
- **Taxi/rideshare receipts** (Uber, Ola) — not in Navan/Concur by default
- **Rail journeys in India** (IRCTC) — no API; would require OCR of IRCTC PDF e-tickets
- **Category 7 (employee commute)** — requires employee survey data, not booking data

### What We'd Ask the PM
*"Does the company reimburse employees for personal car use on company travel? That mileage
data sits in the expenses module (SAP Concur Expense, not Travel). Should we ingest it as
Scope 3 Category 6?"*

---

## Decision 8 — Forecasting: synchronous inline vs async Celery

### The Ambiguity
Generating Holt-Winters ETS with numpy over 12 months of data takes ~50ms. At 100 concurrent
users all triggering forecasts simultaneously, that's 5 seconds of blocking threads.

### What We Chose
**Synchronous inline for Phase 1.** The `ForecastedEmissions` table caches results per FY.
The first request generates and persists; subsequent requests (same FY, same drivers) return
from the DB immediately. Generation is only triggered on cache miss or driver change.

A `FORECAST_ASYNC` setting flag is documented in `forecasting_architecture.md` for Phase 3
(Celery migration). The synchronous path is production-safe for single-digit concurrent users.

### What We'd Ask the PM
*"What is the expected concurrent user count at GA? If it exceeds 20 users doing ESG analysis
simultaneously, we should prioritise the Celery migration before launch."*
