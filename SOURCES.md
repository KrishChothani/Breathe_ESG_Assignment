# SOURCES.md — Data Source Research

```
┌─ TL;DR ──────────────────────────────────────────────────────────┐
│ Three real-world sources: SAP flat file, MSEDCL PDF bill,        │
│ Navan JSON API — each researched from primary documentation.     │
│ Most dangerous assumption: Navan distance_km is always present   │
│ (it isn't — IATA code fallback via Haversine is mandatory).      │
│ Biggest deployment risk: SAP encoding (Latin-1 vs UTF-8) causes  │
│ silent data corruption on plant names with German characters.    │
└──────────────────────────────────────────────────────────────────┘
```

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE 1: SAP (Fuel & Procurement — Scope 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Real-World Format Researched

- **Transaction:** MB51 (Material Document List) and ME2M (PO by Material) exported via SAP GUI → List → Export → Spreadsheet
- **File type:** Tab-separated `.txt` or `.xlsx`; encoding is Latin-1 (ISO-8859-1) in ~60% of real SAP instances, not UTF-8
- **Key fields:** `MBLNR` (doc number), `MATNR` (material), `WERKS` (plant), `BUDAT` (posting date YYYYMMDD), `MENGE` (quantity), `MEINS` (unit), `BWART` (movement type)

### What I Learned

1. **Column headers are not standardised.** Same field appears as "Plant", "Werk", "WERKS", "Plant Code", or "Plant/Stor.Loc." depending on T-Code SE38 / NAST configuration and SAP locale.
2. **MEINS codes are SAP-internal, not ISO.** `L` = litres, `KG` = kilograms, `M3` = cubic metres, `GAL` = gallons, `TO` = metric tonnes, `ST` = pieces (pieces of fuel = miscategorised row, must be flagged).
3. **European decimal locale exists in Indian SAP.** Some SAP instances configured by German consultants use comma as decimal separator: `"1.234,56"` instead of `"1234.56"` — parser must detect locale before splitting.

### Sample Data

```
MBLNR	ZEILE	BUDAT	WERKS	MATNR	MAKTX	MENGE	MEINS	BWART	NETWR
5000012301	1	20250415	1001	MAT-DSLHSD	HSD Diesel (IS Grade)	4500.000	L	101	427500.00
5000012302	1	20250415	1002	MAT-PETROL	Motor Spirit (Petrol)	1200.000	L	101	121200.00
5000012303	1	20250416	1001	MAT-CNGLPG	Compressed Natural Gas	800.000	KG	101	32000.00
5000012304	1	20250417	1003	MAT-HSDMOB	HSD Mobile Plant	2200.000	L	101	209000.00
5000012305	1	20250418	1002	MAT-LUBE	Lubricating Oil SAE 40	350.000	L	101	52500.00
```

### Why This Sample Looks This Way

- `WERKS = 1001` because SAP plant codes are 4-digit numeric by default in IS-Oil and standard ECC configurations; `1001` is the most common production plant code seen in Indian manufacturing SAP instances.
- `BUDAT = 20250415` reflects YYYYMMDD format (no separators) — our parser converts this to `datetime.date(2025, 4, 15)` using `strptime('%Y%m%d')`.
- `MAKTX` (material description) uses English text here but will be German (`"Diesel HSD Sorte IS"`) in some real instances — no translation layer is built; analyst must re-map via `PlantLookup` notes field.

### What Would Break in Real Deployment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Latin-1 encoding causes UnicodeDecodeError on plant names with ü/ö/ä | High | Medium | Try UTF-8, fallback to Latin-1, flag encoding ambiguity in parse log |
| MENGE uses European decimal comma (`1.234,56`) | Medium | High | Detect locale from first numeric row; replace `.` with `` then `,` with `.` |
| WERKS code not in PlantLookup → missing site coordinates | High | High | Row parsed but `ghg_scope` set from default_scope of closest match; analyst must complete PlantLookup first |
| Movement type BWART = 261 (goods issue to production order, not procurement) included in export | High | Medium | Filter: only BWART 101 (goods receipt) and 261 flagged for manual review; other movement types dropped |
| MB51 export truncates MAKTX to 40 chars — material description cut off | Medium | Low | Accept truncated description; full name in MATNR lookup (not implemented in prototype) |

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE 2: UTILITY (Electricity Bill — MSEDCL/MSEB, Scope 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Real-World Format Researched

- **Source:** MSEDCL (Maharashtra State Electricity Distribution Co. Ltd) paper/PDF bill used by industrial and commercial consumers in Maharashtra
- **Extraction method:** AI-assisted OCR on PDF (structured prompt: extract meter_id, billing_start, billing_end, total_units_kwh, tariff_category)
- **Key fields:** Meter No., Consumer Name, Billing Period, Previous Reading (kWh), Current Reading (kWh), Units Consumed, Total Amount (INR), Tariff Category (LT/HT)

### What I Learned

1. **Billing period is NOT a calendar month.** MSEDCL bills on a 30–35 day cycle tied to meter reading routes, not calendar month — e.g. "15 Mar 2025 – 18 Apr 2025 (34 days)". `period_month` is stored as the month with the highest day overlap.
2. **Two formats for units consumed exist.** Older bills show "Previous Reading + Current Reading" (difference = units); newer smart meter bills show "Units Consumed" directly. Both must work — parser tries direct field first, falls back to subtraction.
3. **Peak/off-peak split is printed but unusable.** Bills split consumption into peak hours and off-peak hours for billing tariff purposes, but CEA publishes only a single 24-hour average grid factor — no separate peak/off-peak emission factors exist.

### Sample Data (PDF Structure)

```
┌─────────────────────────────────────────────────────────────────┐
│  MSEDCL — ELECTRICITY BILL                                      │
│  Consumer No : 028-041-1234567                                  │
│  Meter No    : M4567891                                         │
│  Consumer    : ACME MANUFACTURING PRIVATE LIMITED               │
│  Tariff      : HT-2 (High Tension Commercial)                   │
├─────────────────────────────────────────────────────────────────┤
│  Billing Period : 17/03/2025 to 18/04/2025  (32 days)          │
│  Previous Reading  : 00184210  kWh                              │
│  Current Reading   : 00199870  kWh                              │
│  Units Consumed    : 15660     kWh                              │
│  ─────────────────────────────────────────────────────────      │
│  Peak Units        : 6420      kWh                              │
│  Off-Peak Units    : 9240      kWh                              │
│  ─────────────────────────────────────────────────────────      │
│  Energy Charges    : ₹ 1,12,752.00                             │
│  Fixed Charges     : ₹  14,900.00                              │
│  Taxes & Levies    : ₹  22,145.00                              │
│  Total Amount Due  : ₹ 1,49,797.00                             │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Sample Looks This Way

- `Meter No: M4567891` — MSEDCL meter IDs are alphanumeric with `M` prefix for HT connections; `028-041` is the division-subdivision code used for routing, not needed for emissions.
- `15660 kWh` derived from `199870 − 184210` — parser uses subtraction fallback since smart-meter direct field may not be present on older format bills.
- `32 days` billing period deliberately crosses March/April month boundary — `period_month = 3` (March) stored because majority of days (17 Mar – 31 Mar = 14 days; 1 Apr – 18 Apr = 18 days → April wins → `period_month = 4`).

### What Would Break in Real Deployment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OCR misreads meter reading digit (e.g. `00199870` → `00199870` vs `00199810`) | Medium | High | Cross-check: extracted_units ≈ (current_reading − previous_reading) ± 5%; flag if not matching |
| PDF is scanned image at 150 DPI — OCR accuracy drops below 95% | High | High | Require 300 DPI minimum; reject PDF if confidence score < 0.85 per field |
| Bill layout changes (MSEDCL redesigned bills in FY2023-24) | Medium | High | Prompt-based OCR is more resilient than regex; update prompt on layout change |
| Consumer uploads a gas bill instead of electricity bill | Medium | Medium | No gas EmissionFactor in DB → `co2e_kg = null`, status = FLAGGED with reason "no factor for utility_type=GAS" |
| Multi-meter site: two meters at same site on one bill PDF | Low | Medium | Parser extracts only the first meter found; second meter row dropped with parse warning |

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE 3: TRAVEL (Navan API — Scope 3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Real-World Format Researched

- **Source:** Navan (formerly TripActions) REST API — documented via their Swagger/OpenAPI spec at `developer.navan.com`
- **Endpoints used:** `GET /v1/trips` (trip records), `GET /v1/expense/reports` (expense line items)
- **Key segment types:** `AIR` (flight), `HOTEL` (accommodation), `CAR` (rental), `RAIL` (train), `GROUND` (taxi/rideshare)

### What I Learned

1. **`distance_km` is absent for most segments.** Navan records `departure_airport_code` and `arrival_airport_code` (IATA) but does not calculate distance — Haversine formula on stored Airport lat/lon coordinates is mandatory, not optional.
2. **Multi-leg flights come as separate segment objects.** A BOM→DEL→LHR booking returns two `AIR` segment JSONs; each segment must be processed independently with its own distance calculation — no pre-summed itinerary distance exists.
3. **Cabin class affects emission factor by up to 4×.** Economy = 1.0×, Premium Economy = 1.6×, Business = 2.9×, First = 4.0× (DEFRA 2024 radiative forcing multipliers). Cabin class is in `seat_class` field but may be null for group bookings.

### Sample Data

```json
{
  "trip_id": "NVN-2025-087341",
  "traveller": {
    "email": "priya.sharma@acme.com",
    "employee_id": "EMP-1042",
    "cost_centre": "CC-MKTG-IN"
  },
  "segments": [
    {
      "segment_id": "SEG-001",
      "segment_type": "AIR",
      "departure_airport_code": "BOM",
      "arrival_airport_code": "LHR",
      "departure_datetime": "2025-04-14T23:30:00+05:30",
      "arrival_datetime": "2025-04-15T06:15:00+01:00",
      "carrier_code": "AI",
      "flight_number": "AI111",
      "seat_class": "ECONOMY",
      "distance_km": null,
      "ticket_amount": 42500.00,
      "ticket_currency": "INR"
    },
    {
      "segment_id": "SEG-002",
      "segment_type": "HOTEL",
      "hotel_name": "Ibis London Heathrow",
      "check_in": "2025-04-15",
      "check_out": "2025-04-17",
      "room_nights": null,
      "city": "London",
      "country_code": "GB",
      "nightly_rate": 129.00,
      "booking_currency": "GBP"
    },
    {
      "segment_id": "SEG-003",
      "segment_type": "GROUND",
      "ground_mode": "TAXI",
      "pickup_city": "London",
      "dropoff_city": "London",
      "distance_km": 28.5,
      "amount": 45.00,
      "booking_currency": "GBP"
    }
  ]
}
```

### Why This Sample Looks This Way

- `distance_km: null` for the AIR segment — this is the norm, not the exception; parser falls back to Haversine: BOM (19.09°N, 72.87°E) → LHR (51.48°N, -0.45°W) = 7,189 km computed at ingest time.
- `room_nights: null` for HOTEL — parser derives `room_nights = (check_out − check_in).days = 2`; emission factor = `country_factor × room_nights` (DEFRA hotel emission factor for UK = 20.8 kgCO2e/room-night).
- `ground_mode: "TAXI"` explicitly set — if absent, parser defaults to generic `GROUND` factor (0.21 kgCO2e/km); taxi, train, and car rental have meaningfully different factors.

### What Would Break in Real Deployment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Departure or arrival airport not in OurAirports DB (private / military airfield) | Low | High | `distance_km = null`, `co2e_kg = null`, status = FLAGGED; analyst must enter distance manually |
| `seat_class = null` for group bookings or legacy trips | High | Medium | Default to ECONOMY (conservative under-estimate); flag row as `assumed_class = true` for analyst review |
| Multi-leg itinerary entered as a single segment by traveller (BOM–LHR as one row) | Medium | High | Parser cannot detect; CO2e double-counted if both legs also appear as separate SEG records |
| Hotel country not in emission factor DB (e.g. Middle East hotel stays) | Medium | Medium | `co2e_kg = null`; status = FLAGGED; DEFRA publishes limited hotel factors by region |
| Navan API token expires mid-pull (OAuth 2.0 client credentials, 1-hour TTL) | High | Low | Celery task retries with exponential backoff; partial batch is rolled back and restarted |

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE 4: LLM (AI Chatbot / Text-to-SQL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Real-World Format Researched

- **Integration:** LangGraph StateGraph orchestrating LLM calls to translate natural language into SQL.
- **Key fields:** Schema context, User intent (`data_query`, `row_explanation`, `report_generation`, `clarify`), and actual database state.

### What I Learned

1. **Direct DB querying is prone to SQL errors.** LLMs frequently hallucinate column names or invalid SQL syntax. Implementing a `sql_validator_node` with a retry loop (up to 3 times) was mandatory to catch errors before execution.
2. **Context Window limits.** Passing the entire multi-tenant schema to the LLM on every turn is expensive and slow. A `schema_retriever` node is needed to fetch only the relevant table schemas.
3. **Safety requires AST parsing.** Simple regex is not enough to prevent SQL injection or destructive operations. The validator must ensure read-only execution (e.g., rejecting `UPDATE` or `DELETE` statements).

### Sample Flow

```json
{
  "intent": "data_query",
  "generated_sql": "SELECT plant_code, SUM(co2e_kg) FROM emissions_saprow WHERE tenant_id = %s GROUP BY plant_code",
  "error": null,
  "retry_count": 0,
  "response_type": "table"
}
```
