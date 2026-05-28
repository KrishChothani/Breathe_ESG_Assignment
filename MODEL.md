# MODEL.md — BreatheESG Data Model

> **This document explains every table in the system, the rationale behind the schema,
> and how three fundamental requirements are satisfied: multi-tenancy, Scope classification,
> and immutable audit trail.**

---

## 1. Core Design Philosophy

Three constraints shaped every table decision:

1. **No cross-tenant data leakage** — a row belonging to Org A must be unreachable by Org B at the ORM layer, not just the API layer.
2. **Source of truth is preserved at rest** — every normalised row retains a pointer to the raw file that produced it, the exact emission factor UUID used, and the human-readable calculation formula. If a factor changes next year, the historical row still shows what was used in FY 2024-25.
3. **Status is a state machine, not a boolean** — `PENDING → APPROVED` is insufficient for SEBI BRSR assurance. The full lifecycle is `PENDING → FLAGGED → APPROVED → LOCKED`, with every transition written to an immutable `AuditLog`.

---

## 2. Multi-Tenancy Architecture

### Decision: Shared Schema with Row-Level Tenant FK

We chose **shared schema / shared database** over schema-per-tenant or database-per-tenant.

```
┌─────────────────────────────────────────────────┐
│                  PostgreSQL DB                   │
│  ┌─────────────┐    ┌─────────────┐             │
│  │ organisations│    │    users    │             │
│  └──────┬──────┘    └──────┬──────┘             │
│         │ FK                │ FK                 │
│         ▼                   ▼                   │
│  ┌──────────────────────────────────────────┐   │
│  │           TenantModel (abstract)          │   │
│  │  organisation FK  +  created_at/updated_at│   │
│  └─────────┬──────────────────────┬──────────┘   │
│            │                      │              │
│      SAPRow, UtilityRow,    PlantLookup,         │
│      TravelRow,             GridEmissionFactor,  │
│      ForecastedEmissions    AirportLookup        │
└─────────────────────────────────────────────────┘
```

**Why not schema-per-tenant?**
- At the 1–50 tenant scale this system targets, schema-per-tenant adds migration complexity with zero performance benefit.
- A B-tree index on `organisation_id` (UUID FK) over a 10M-row table is faster than a schema switch round-trip.
- Django's migration system does not support per-schema migrations without third-party packages.

**Enforcement (core/models.py):**

```python
class TenantModel(TimeStampedModel):
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
    )
    class Meta:
        abstract = True
```

Every model holding business data (`SAPRow`, `UtilityRow`, `TravelRow`, `ForecastedEmissions`,
`PlantLookup`, `GridEmissionFactor`, `AirportLookup`, `TravelEmissionFactor`) extends `TenantModel`.
The `organisation` FK is **never nullable** — enforced at the DB level.

The JWT token payload carries `org_slug`. The `get_active_organisation(request)` helper resolves
the `Organisation` on every authenticated request, and every queryset is pre-filtered before returning.

---

## 3. The `RawUpload` — Source-of-Truth Anchor

```
RawUpload
  ├── id (UUID, PK)
  ├── organisation FK        ← tenant scope
  ├── source_type            ← SAP | UTILITY | TRAVEL
  ├── file                   ← S3/local path to the original file bytes
  ├── original_filename      ← preserved exactly as received
  ├── status                 ← UPLOADED → PROCESSING → DONE | FAILED | OCR_EXTRACTED
  ├── row_count              ← how many rows were parsed
  ├── error_log (JSON)       ← list of per-row parse failures with line numbers
  ├── uploaded_by FK         ← user who triggered ingest
  └── created_at / updated_at
```

**Why `RawUpload` is the root anchor:**

Every `SAPRow`, `UtilityRow`, and `TravelRow` has a non-nullable FK to `RawUpload`. This means:
- "Where did this number come from?" — navigate `NormalisedRow.raw_upload.file`.
- If a file was ingested in error, cascade-deleting `RawUpload` removes all derived rows atomically.
- `row_count` enables completeness checks: if a 500-row CSV produced only 480 `SAPRow`s, the 20 failures are in `error_log`.

---

## 4. `NormalisedRow` — Abstract Base for All Emission Rows

```
NormalisedRow (abstract — never instantiated directly)
  ├── id (UUID, PK)
  ├── organisation FK           ← from TenantModel
  ├── raw_upload FK             ← source-of-truth pointer (non-nullable)
  ├── status                    ← PENDING | FLAGGED | APPROVED | REJECTED | LOCKED | PARSE_FAILED
  ├── anomaly_flags (JSON)      ← machine-detected issues: ["MAJOR_VARIANCE", "MISSING_EF"]
  ├── parse_error (text)        ← empty if OK; full traceback if PARSE_FAILED
  ├── co2e_kg (Decimal 12,4)    ← THE canonical emission value in kg CO2e
  ├── ghg_scope                 ← SCOPE_1 | SCOPE_2 | SCOPE_3
  ├── ghg_category              ← "stationary_combustion", "purchased_electricity", ...
  │
  ├── emission_factor_value     ← numeric factor snapshot (e.g. 0.710)
  ├── emission_factor_unit      ← "kg CO2e / kWh"
  ├── emission_factor_source    ← DEFRA_2024 | IPCC_AR6 | ICAO_2023 | CEA_V20 | CUSTOM
  ├── emission_factor_year      ← calendar year the factor applies to
  ├── emission_factor_record_id ← UUID of the EmissionFactor registry row used
  └── formula (text)            ← "4,280 kWh × 0.710 = 3,038.80 kg CO2e"
```

### Why `co2e_kg` is Decimal, not Float

Floating-point arithmetic accumulates rounding error when summed across thousands of rows.
Annual BRSR totals are reported to 2 decimal places under external assurance. Using
`DecimalField(max_digits=12, decimal_places=4)` ensures aggregation results are deterministic
across any PostgreSQL version.

### Why the Emission Factor is Stored Three Ways

| Field | Purpose |
|---|---|
| `emission_factor_record_id` (UUID) | Audit FK — points to the exact versioned `EmissionFactor` row current at ingestion time |
| `emission_factor_value` + `emission_factor_unit` | Denormalised snapshot — factor value at calculation time, preserved even if the registry row is updated or superseded |
| `formula` (text) | Human-readable — an SEBI external auditor can verify the arithmetic without any database access |

This is **intentional redundancy**. It prevents "factor drift" — updating an `EmissionFactor`
registry entry for a new FY must never silently change historical calculations from a prior FY.

> **Note on the EmissionFactor join:** `emission_factor_record_id` is a plain `UUIDField`,
> **not a `ForeignKey`**. If a factor row is hard-deleted for compliance reasons, the historical
> calculation value is still preserved in `emission_factor_value`. A hard FK would cascade-null
> that reference, destroying audit evidence.

---

## 5. The Three Concrete Row Types

### 5.1 `SAPRow` — Scope 1 Direct Emissions (Fuel Procurement)

```
SAPRow extends NormalisedRow
  ├── po_number / line_item      ← SAP Purchase Order + line item
  ├── material_code              ← SAP MATNR
  ├── material_description       ← human-readable fuel name
  ├── plant_code                 ← SAP WERKS code → joins PlantLookup
  ├── plant_name                 ← denormalised for query performance
  ├── vendor_id                  ← SAP LIFNR
  ├── quantity                   ← raw quantity in unit_original
  ├── unit_original              ← SAP MEINS code ("L", "KG", "M3", "GAL")
  ├── unit_normalised            ← canonical ISO unit ("litres", "kg")
  ├── net_value / currency       ← procurement cost in original currency
  ├── document_date              ← posting date — used for India FY assignment
  ├── esg_category               ← "diesel" | "petrol" | "cng" | "lpg" | "hsd"
  └── CO2 comparison:
      ├── document_claimed_co2_kg   ← what supplier invoice states
      ├── system_calculated_co2_kg  ← what BreatheESG engine computes
      ├── co2_variance_pct          ← |doc − system| / system × 100
      └── co2_comparison_status     ← NOT_APPLICABLE | MATCH | MINOR_VARIANCE | MAJOR_VARIANCE
```

### 5.2 `UtilityRow` — Scope 2 Purchased Electricity

```
UtilityRow extends NormalisedRow
  ├── account_number / meter_id  ← DISCOM account and meter identifiers
  ├── site_name                  ← building or plant name
  ├── billing_start / billing_end ← bill period (30-60 day billing lag common)
  ├── period_month (indexed)     ← "2025-06" — enables O(1) monthly aggregation
  ├── consumption_original       ← as received (kWh, MWh, or "Units")
  ├── unit_original              ← raw unit from the bill
  ├── consumption_kwh            ← normalised to kWh — all math uses this
  ├── grid_factor_used           ← CEA factor applied (kg CO2e / kWh)
  ├── grid_factor_vintage_year   ← calendar year of the CEA publication
  └── CO2 comparison (same pattern as SAPRow)
```

### 5.3 `TravelRow` — Scope 3 Business Travel

```
TravelRow extends NormalisedRow
  ├── navan_trip_id / external_trip_id  ← idempotency key from Navan/Concur
  ├── traveller_email / traveler_employee_id
  ├── segment_type  ← AIR | HOTEL | CAR | RAIL | GROUND_TRANSPORT
  │
  ├── [AIR]   departure_airport_code, arrival_airport_code, airline_carrier,
  │            cabin_class (ECONOMY|PREMIUM_ECONOMY|BUSINESS|FIRST),
  │            stops, rfi_applied (Radiative Forcing Index boolean)
  │
  ├── [HOTEL] hotel_name, check_in_date, check_out_date,
  │            number_of_nights, number_of_rooms, hotel_country
  │
  ├── [CAR]   car_vendor, car_category, fuel_type,
  │            car_pickup_datetime, car_dropoff_datetime
  │
  ├── [RAIL]  rail_carrier, departure_station, arrival_station, rail_class
  │
  └── distance_km, distance_source ("HAVERSINE" | "ICAO_TABLE" | "REPORTED"),
      distance_estimated (bool), cost_amount, cost_currency
```

---

## 6. `EmissionFactor` — Global Factor Registry

```
EmissionFactor (NOT tenant-scoped — shared reference table)
  ├── scope                     ← SCOPE_1 | SCOPE_2 | SCOPE_3
  ├── fuel_or_activity_type    ← "diesel" | "electricity_india" | "flight_short_haul"
  ├── factor_value              ← numeric (e.g. 2.6533 for diesel)
  ├── factor_unit               ← "kg CO2e / litre"
  ├── source_name               ← CEA_V20 | DEFRA_2024 | IPCC_AR6 | ICAO_2023 | INDIA_GHG
  ├── source_version            ← "V20.0 (2024 Publication)"
  ├── valid_from_fy / valid_to_fy ← India FY validity window ("2024-25" / null = current)
  ├── country_code              ← "IN" default (CEA factors are India-specific)
  ├── is_active                 ← false = superseded; never deleted
  └── unique_together: (scope, fuel_or_activity_type, valid_from_fy, country_code)
```

**Why global, not tenant-scoped?**

`EmissionFactor` is seeded from official regulatory publications. It is a reference table, not
operational data. Tenants reference it via `emission_factor_record_id` but cannot modify it.
Tenant-specific overrides use `GridEmissionFactor` (electricity) and `TravelEmissionFactor`
(travel) which are tenant-scoped.

---

## 7. Audit Trail System

### 7.1 `AuditLog` — Immutable Event Log

```python
class AuditLog(models.Model):
    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionDenied("AuditLog records are immutable.")
    def delete(self, *args, **kwargs):
        raise PermissionDenied("AuditLog records cannot be deleted.")
```

Fields: `organisation`, `row_id`, `row_source` (SAP/UTILITY/TRAVEL), `action`
(INGESTED | FLAGGED | APPROVED | REJECTED | RESUBMITTED | COMMENT_ADDED | EXPORTED),
`performed_by`, `performed_at`, `previous_status`, `new_status`, `note`, `ip_address`, `source_file`.

### 7.2 `RowComment` — Partially Immutable Findings

`body`, `is_finding`, and `author` are immutable after creation. Only `resolved` / `resolved_by` /
`resolved_at` can be updated — closing a finding without erasing the original concern.

### 7.3 Status State Machine

```
PARSE_FAILED ─────────────────────────── (terminal)
PENDING ──► FLAGGED ──► APPROVED ──► LOCKED
     └───────────────► APPROVED ──► LOCKED
     └──────────────────────────► REJECTED (terminal)
```

`LOCKED` = row included in an export to the external auditor. API rejects status changes
on `LOCKED` rows except from a superuser account.

---

## 8. `ForecastedEmissions` — Projections in a Separate Table

Fields: `financial_year`, `month_number` (1=Apr…12=Mar), `scope`, `co2e_tonnes_central`,
`co2e_tonnes_lower/upper` (90% CI), `forecast_method` (RUN_RATE | ETS | ACTIVITY_DRIVEN | NOWCAST),
`confidence_pct`, `is_nowcast`, `rmsfe`, `activity_driver_air/hotel/ground`,
`unique_together: (organisation, financial_year, month_number, scope)`.

**Structural separation from actuals is intentional.** An auditor running SEBI BRSR verification
must be able to get clean actuals with no WHERE clause gymnastics. Projections live in a different
table with a different lifecycle (regenerated on demand; not audit-logged).

---

## 9. Unit Normalisation

| Dimension | Canonical unit | Display unit |
|---|---|---|
| Energy | kWh | kWh / MWh |
| Fuel mass | kg or litres (fuel-specific) | — |
| Distance | km | km |
| Emissions (storage) | **kg CO2e** (Decimal 12,4) | — |
| Emissions (display/BRSR) | **tCO2e** (÷ 1000) | rounded to 2 d.p. |
| Money | original currency preserved | INR for SEBI intensity ratios |

SAP MEINS code normalisation on ingestion:
```
"L"   → litres (×1)
"KG"  → kg     (×1)
"M3"  → litres (×1000, for LPG/CNG gas volumes)
"GAL" → litres (×3.78541)
"TO"  → kg     (×1000, metric tonnes)
```
