# TRADEOFFS.md — Three Things Deliberately Not Built

> **Each entry states what was not built, what was built instead, and the explicit
> tradeoff being made. These are engineering decisions, not oversights.**

---

## Tradeoff 1 — Real-Time Streaming Ingestion vs Batch File Upload

### What Was Not Built
A real-time data pipeline using webhooks or streaming APIs. In production ESG platforms,
Concur and Navan both offer real-time webhooks that push travel bookings as they happen.
SAP can be configured to push purchase document events via IDoc or RFC. This would eliminate
the need for file uploads entirely and give sub-minute data latency.

### What Was Built Instead
A **batch file upload** model. The user uploads a CSV/Excel export from their system. The
`RawUpload` table tracks the file, a background parser creates `NormalisedRow` records, and
the upload is processed in one atomic transaction.

### The Explicit Tradeoff

| Dimension | Real-Time Streaming | Batch File Upload (built) |
|---|---|---|
| Data freshness | Sub-minute | Days (upload cadence) |
| Infrastructure | Kafka/SQS + consumer workers | Standard Django + file storage |
| Error handling | Per-event, complex retry logic | Per-file, single `error_log` JSON |
| Auditability | Harder (stream is ephemeral) | Easier (`RawUpload` is the durable anchor) |
| Implementation time | 3–4× longer | Baseline |

**Why this tradeoff makes sense for BRSR:**

SEBI BRSR is an annual disclosure, not a live dashboard. Data is reviewed and approved by
a compliance officer before it enters the report. A batch model that preserves the exact
uploaded file as the audit anchor (`RawUpload.file`) is actually *more* auditable than a
stream where the original source event is ephemeral. The external assurer can download the
exact file that produced the numbers.

Real-time streaming would be the right call for an operational energy management system
where alerts on consumption spikes have economic value. For BRSR disclosure, batch is sufficient
and architecturally cleaner.

---

## Tradeoff 2 — Automated ML-Based Scope Classification vs Rule-Based + Manual Override

### What Was Not Built
A machine learning classifier that reads material descriptions, vendor names, and procurement
patterns to automatically assign `SCOPE_1`, `SCOPE_2`, or `SCOPE_3` with high precision.
This is technically tractable: fine-tuned BERT on ESG procurement datasets achieves ~92%
accuracy on scope classification benchmarks.

### What Was Built Instead
A **deterministic rule-based classifier** with a manual override mechanism:

1. `PlantLookup.default_scope` — admin-configured per SAP WERKS code
2. Keyword matching on `esg_category` — regex patterns against material description
3. Manual override — any `PENDING/FLAGGED` row's `ghg_scope` can be changed; change is audit-logged

### The Explicit Tradeoff

| Dimension | ML Classifier | Rule-Based (built) |
|---|---|---|
| Accuracy | ~92% on benchmark data | ~85% on well-configured systems |
| Explainability | Low (black box) | High (auditor can trace rule) |
| Regulatory acceptability | Questionable under SEBI assurance | Clean |
| Edge case handling | Trained on historical data, fails on new material types | Fails predictably, surfaced as FLAGGED |
| Maintenance | Requires periodic retraining | Rules updated by admin |

**Why this tradeoff makes sense for BRSR:**

SEBI BRSR Core (Circular July 2023) requires external assurance from FY 2025-26 for the
top 500 listed entities. An external assurer performing reasonable assurance over GHG emissions
must be able to trace every classification decision to a documented rule. "The ML model predicted
Scope 1 with 87% confidence" is not a defensible audit response.

The rule-based system fails more loudly (FLAGGED status, human review) and the failure is
traceable. The ML system fails more quietly (wrong scope, no alert) and the failure is invisible
until an auditor catches it three months later.

---

## Tradeoff 3 — Per-Gas GHG Breakdown vs CO2e-Only Reporting

### What Was Not Built
A full multi-gas GHG inventory tracking CO₂, CH₄, N₂O, HFCs, PFCs, SF₆, and NF₃ separately.
SEBI BRSR Core (under SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122) explicitly mentions that Scope 1
should be broken down by gas type "where available." GHG Protocol's corporate standard has always
required this breakdown for a complete inventory.

### What Was Built Instead
**CO2e-only reporting**, where all gases are converted to carbon dioxide equivalent at ingestion
time using IPCC AR6 Global Warming Potential values, and stored as a single `co2e_kg` field.

The conversion happens implicitly in the emission factor: the `EmissionFactor.factor_value`
for diesel (2.6533 kg CO2e / litre) already incorporates the CH₄ and N₂O components using
AR6 100-year GWP values (CH₄ = 27.9, N₂O = 273).

### The Explicit Tradeoff

| Dimension | Per-Gas Breakdown | CO2e-Only (built) |
|---|---|---|
| SEBI BRSR compliance | Fully compliant (gas-level detail) | Compliant where gas data unavailable |
| Data availability | Requires fuel-specific gas emission factors and metering | Any procurement data with quantity |
| Schema complexity | 7+ gas columns per row + GWP lookup table | 1 decimal field |
| Auditor utility | Enables gas-specific reduction target tracking | Enables total GHG management |
| Data sources required | Process-level measurement for CH₄/N₂O | Standard procurement export |

**Why this tradeoff makes sense here:**

The practical reality is that Indian manufacturing companies generating SAP procurement exports
do not have process-level CH₄ and N₂O measurements from combustion equipment. The data
literally does not exist in the source systems. Building a schema that demands gas-level
breakdown would result in 90% null columns.

The SEBI carve-out "where available" acknowledges this. The CO2e-only approach is compliant,
matches what the source data can actually support, and avoids a false precision problem where
displaying "CO₂: 1,247t, CH₄: 0t, N₂O: 0t" would imply zero fugitive emissions rather than
"not measured."

**What would trigger building this:**

If a client has direct emissions from industrial processes (cement kiln, steel furnace, chemical
reactor), those process emissions require CH₄/N₂O metering and a per-gas breakdown becomes
both possible and mandatory. The schema change would add `co2_kg`, `ch4_kg_co2e`, `n2o_kg_co2e`
columns to `NormalisedRow` and a `GWPLookup` table.
