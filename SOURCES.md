# SOURCES.md — The Three Data Sources

> **For each source: the real-world format researched, what we learned, what the sample data
> looks like and why, and what would break in a real deployment.**

---

## Source 1 — SAP Procurement Export (Scope 1)

### Real-World Format Research

SAP ERP (ECC 6.0 and S/4HANA) exposes procurement data via two primary transactions:

**ME2M** — Purchase Orders by Material
- Accessed via: SAP GUI → Logistics → Materials Management → Purchasing → Purchase Order → List Displays → By Material
- Export: "List → Export → Spreadsheet" produces a `.xlsx` or `.txt` file with SAP list formatting
- Header row: Often absent or in German ("Bestellnummer", "Pos.", "Werk", "Menge", "Einheit")
- Known variants: Tab-separated, semicolon-separated, pipe-separated depending on SAP locale and version

**MB51** — Material Documents (Goods Receipts)
- Used when the goods receipt (GR) date is more accurate than the PO date for FY assignment
- Contains: `MBLNR` (material document), `MATNR` (material), `WERKS` (plant), `BUDAT` (posting date), `MENGE` (quantity), `MEINS` (unit)

**What We Learned**

1. **Encoding issues are universal.** SAP exports are frequently Latin-1 (ISO-8859-1), not UTF-8. German special characters (ü, ö, ä) in plant names will corrupt on UTF-8 parse. The parser must attempt UTF-8, fall back to Latin-1, and flag rows where the encoding is ambiguous.

2. **Column names are not standardised.** Different SAP instances configure different column labels. A WERKS column might be labelled "Plant", "Werk", "WERKS", "Plant Code", or "Plant / Storage Location" depending on the user's SAP customization (T-Code SE38 / NAST). Hard-coding column names fails; fuzzy column matching by position and content is required.

3. **MEINS codes are SAP-internal.** SAP uses MEINS (Unit of Measure) codes that are not ISO. Common codes: `L` (litres), `KG` (kilograms), `M3` (cubic metres), `GAL` (gallons), `TO` (metric tonnes), `ST` (pieces — which has no energy meaning and indicates a miscategorised fuel row). A normalisation table is essential.

4. **WERKS codes are company-specific.** There is no global WERKS code standard. `1000` is SAP's default training plant. A real company might use `IN01`, `IN_MUM`, `1001`, or `CORP`. The same WERKS code means different things at different companies. This is why `PlantLookup` is tenant-scoped.

5. **The "net value" field (NETWR) is unreliable for CO2 claims.** Some companies annotate SAP POs with a CO2 figure from their supplier's EPD (Environmental Product Declaration). This figure appears inconsistently — sometimes in a custom Z-field, sometimes in a text field, sometimes absent. The `document_claimed_co2_kg` vs `system_calculated_co2_kg` comparison mechanism handles this.

### What Our Sample Data Looks Like

```
PO Number | Line | Material   | Description           | Plant | Qty    | UoM | Net Value | Currency | Doc Date   | ESG Cat
1800001234| 0010 | MAT-DSL-01 | HSD Diesel Grade A    | IN01  | 5000   | L   | 425000.00 | INR      | 2025-06-15 | diesel
1800001234| 0020 | MAT-DSL-01 | HSD Diesel Grade A    | IN01  | 3200   | L   | 272000.00 | INR      | 2025-07-02 | diesel
1800001235| 0010 | MAT-PET-02 | Petrol (MS) 91 Oct    | IN02  | 1800   | L   | 198000.00 | INR      | 2025-08-10 | petrol
1800001236| 0010 | MAT-CNG-03 | CNG Compressed Gas    | IN01  | 820    | KG  | 41000.00  | INR      | 2025-09-05 | cng
```

**Why these choices:**
- Two line items on the same PO test the `(po_number, line_item)` composite uniqueness
- Different plants (`IN01`, `IN02`) test the `PlantLookup` resolution and plant-level aggregation
- CNG in `KG` (not litres) tests the MEINS normalisation — CNG is sold by mass, not volume
- `ESG Cat` column is pre-classified (real deployments have this mapped by the admin before first upload)

### CO2e Calculation

```
5,000 L diesel × 2.6533 kg CO2e/L = 13,266.50 kg CO2e
Formula stored: "5,000.00 L × 2.6533 kg CO2e/L = 13,266.50 kg CO2e"
Factor source: DEFRA_2024 / DESNZ (UK GHGC Conversion Factors 2024)
```

**Note:** DEFRA 2024 is used for diesel because IPCC AR6 does not provide country-specific fuel
factors. India's own GHG Program factors are derived from IPCC 2006 — DEFRA 2024 is the most
frequently updated and internationally accepted fuel combustion factor set.

### What Would Break in Real Deployment

1. **Column header detection.** If a company exports ME2M with German headers and no English configuration, the parser fails to find "Plant" and all plant codes come in as null. Fix: build a column alias table per company, configurable by admin.

2. **Multi-level headers.** SAP list exports sometimes produce a two-row header where row 1 is "Purchase Document" spanning 3 columns and row 2 is "Number | Item | Status". The parser currently assumes single-row headers.

3. **Merged cells / subtotal rows.** SAP's ALV grid inserts subtotal rows when the user groups by plant or material group. These rows have no `MATNR` or `MENGE` and will fail parse, inflating the `error_log`.

4. **WERKS codes not in `PlantLookup`.** The company adds a new factory mid-year. The WERKS code `IN05` appears in the export but has no `PlantLookup` entry. The parser creates the `SAPRow` but `ghg_scope` is null and the row is `FLAGGED`. An admin must add the plant before the row can be approved.

5. **Encoding corruption on special characters.** A vendor name with "ü" (German) or "à" (French) in a Latin-1 file processed as UTF-8 produces replacement characters. The `material_description` field ends up as "H÷chster GmbH", which is incorrect but not a parse failure.

---

## Source 2 — Utility Portal CSV (Scope 2)

### Real-World Format Research

Indian electricity bills are issued by DISCOMs (Distribution Companies) like BESCOM (Bangalore),
BSES (Delhi), Torrent Power (Ahmedabad), TPDDL (Delhi), and MSEDCL (Maharashtra). Each DISCOM
has a different billing portal with different CSV export formats.

**What We Learned**

1. **No standard format exists.** Unlike SAP (which has at least an internal consistency within a company), DISCOM portal exports have zero standardisation. BESCOM exports a 4-column CSV; MSEDCL exports a 14-column Excel with merged header cells; Torrent Power emails PDF bills (requiring OCR).

2. **Billing periods are not calendar months.** Most Indian DISCOMs bill on a 60-day cycle (bimonthly), not monthly. A single bill covers April 15 – June 14. Assigning this to India FY months requires proration logic (not currently implemented — billing start month is used as proxy).

3. **"Units" vs kWh vs MWh.** Industrial consumers receive bills in kWh or MWh. Commercial consumers receive bills in "Units" (which are kWh at 1:1 ratio). Very large consumers (HT connections) receive in MWh. The `unit_original` field preserves what was received; `consumption_kwh` is always normalised.

4. **Net metering complicates consumption.** Companies with rooftop solar have net-metered accounts. The utility bill shows import consumption minus solar export. Using import-only (gross) consumption is required for Scope 2 accounting; using net consumption understates market-based emissions and overstates avoided emissions. Our parser uses `consumption_kwh` which is whatever the bill states — whether net or gross depends on the account type.

5. **The 30–60 day billing lag.** A bill for energy consumed in April 2025 is issued on June 3, 2025 and uploaded on June 20, 2025. This is why the Nowcasting module (Formula 6) exists — to estimate missing recent months from prior-year seasonal proxies.

6. **CO2 factors on the bill.** Some DISCOMs (notably BSES) print a CO2 figure on the bill. This figure uses the DISCOM's own average factor, which may be outdated or use a different GWP base year than CEA V20. The `document_claimed_co2_kg` vs `system_calculated_co2_kg` comparison captures this discrepancy.

### What Our Sample Data Looks Like

```
Account Number | Meter ID    | Site Name        | Bill Start | Bill End   | Consumption | Unit | Grid Factor | Grid Year
ACC-BLR-001    | MTR-BLR-001 | Bangalore HQ     | 2025-04-01 | 2025-04-30 | 4280.00     | kWh  | 0.710       | 2024
ACC-BLR-001    | MTR-BLR-002 | Bangalore DC     | 2025-04-01 | 2025-04-30 | 12750.00    | kWh  | 0.710       | 2024
ACC-MUM-002    | MTR-MUM-001 | Mumbai Office    | 2025-04-01 | 2025-04-30 | 3100.00     | kWh  | 0.710       | 2024
ACC-DEL-003    | MTR-DEL-001 | Delhi Branch     | 2025-05-01 | 2025-05-31 | 8900.00     | kWh  | 0.710       | 2024
ACC-BLR-001    | MTR-BLR-001 | Bangalore HQ     | 2025-06-01 | 2025-06-30 | 4650.00     | kWh  | 0.710       | 2024
```

**Why these choices:**
- Multiple meters at the same account (`MTR-BLR-001`, `MTR-BLR-002`) test multi-meter aggregation
- Same meter across months tests the `period_month` indexed aggregation
- Delhi bill starts May (not April) — reflects real billing cycle misalignment
- CEA V20 FY 2024-25 factor: 0.710 kg CO2e / kWh (India national average, location-based)

### CO2e Calculation

```
4,280 kWh × 0.710 kg CO2e/kWh = 3,038.80 kg CO2e
Formula stored: "4,280.00 kWh × 0.710 kg CO2e/kWh = 3,038.80 kg CO2e"
Factor source: CEA CO2 Baseline Database V20.0 (FY 2024-25)
```

### What Would Break in Real Deployment

1. **PDF-only bills.** ~30% of Indian utility connections (especially old HT connections) issue only PDF bills. The `RawUpload.status = 'OCR_EXTRACTED'` state exists for this, but the OCR pipeline (Google Document AI or AWS Textract) is not implemented. These bills would have to be manually transcribed.

2. **Bimonthly billing periods crossing FY boundary.** A bill from March 2 – April 30 spans two India FYs. The system currently assigns the entire consumption to the `billing_start` month (March = FY 2024-25). A strict BRSR treatment would require proration: 29 days to FY 2024-25, 30 days to FY 2025-26. This is not implemented.

3. **Net metering rooftop solar.** If the company has solar installations, the utility bill shows net consumption (import − export). SEBI BRSR Scope 2 requires gross import consumption for location-based accounting and separately discloses renewable energy certificates (RECs) for market-based accounting. Importing net-metered bills without adjustment understates Scope 2.

4. **DISCOM format changes.** DISCOMs update their portal formats without notice. A format that worked in April may have new columns in October. The parser needs a per-DISCOM format version registry to detect and alert on format changes.

5. **Multiple DISCOMs at the same site.** A large campus may have electricity from BESCOM for offices and a separate captive power generator (Scope 1) for manufacturing. If both appear in the utility CSV, the parser cannot distinguish them without a site-level configuration flag.

---

## Source 3 — Corporate Travel API / Export (Scope 3)

### Real-World Format Research

The two dominant corporate travel management platforms in India for listed companies are:

**Navan** (formerly TripActions): Used by mid-market and enterprise. Provides:
- REST API (OAuth 2.0): `/v1/trips`, `/v1/segments`, `/v1/receipts`
- CSV export: Trip report with one row per booking segment
- Webhook: POST to customer endpoint on booking/cancellation events

**SAP Concur**: Used by large enterprises with existing SAP ERP. Provides:
- Standard Extract file format (`.csv`, one row per expense line)
- Travel Allowance Import/Export
- Standard Analytics reports in Excel

**What We Learned**

1. **Segment granularity vs trip granularity.** Concur exports are trip-level by default (one row per trip with total cost). Navan exports are segment-level (one row per flight leg, one row per hotel night). For GHG accounting, segment-level is required — a connecting flight has different distance than a direct flight. The `TravelRow` model is segment-level; trip-level data requires expansion logic.

2. **IATA code ambiguity.** Airport IATA codes are the foundation of air distance calculation, but they are not globally unique for all time periods. Small regional airports sometimes change IATA codes. The `Airport` table (from OurAirports) is loaded with current IATA codes; retired codes require a separate alias table.

3. **The Radiative Forcing Index (RFI).** Aviation emissions at altitude cause additional warming beyond the CO2 from fuel burn — through contrail formation and NOx chemistry. DEFRA recommends applying an RFI multiplier of 1.9 to flight emissions (i.e., actual warming impact is 1.9× the CO2 equivalent of fuel burn alone). This is controversial — SEBI BRSR does not mandate RFI, and ICAO's calculator does not include it. We store `rfi_applied` as a boolean per segment so clients can choose.

4. **Hotel emission factors are highly uncertain.** DEFRA 2024 provides hotel factors by region (UK: 31 kg CO2e / room / night; India: similar order of magnitude). But a 5-star hotel in Mumbai will have very different energy intensity from a budget hotel in Pune. Without building-level energy data (which hotels don't share), a regional average is the best available.

5. **Cabin class matters significantly.** Business class is allocated ~3× the floor space of economy on wide-body aircraft. Per-passenger emissions in business are therefore ~3× higher than economy per passenger-km. The `cabin_class` field (ECONOMY | PREMIUM_ECONOMY | BUSINESS | FIRST) feeds into the per-pax emission factor selection.

6. **Employee personal data.** Travel data contains `traveller_email` and `traveler_employee_id`. This is PII under India's PDPB (Personal Data Protection Bill) and GDPR for European operations. Storing email in `TravelRow` creates a compliance obligation: these rows must be masked or pseudonymised before export to external auditors.

### What Our Sample Data Looks Like

**Air segment:**
```
Trip ID      | Traveller Email         | Seg Type | Travel Date | From | To  | Airline | Cabin   | Distance | Co2e kg
TRIP-2025-001| alice@company.com       | AIR      | 2025-05-10  | BLR  | DEL | 6E      | ECONOMY | 1741     | 266.61
TRIP-2025-001| alice@company.com       | AIR      | 2025-05-14  | DEL  | BLR | 6E      | ECONOMY | 1741     | 266.61
TRIP-2025-002| bob@company.com         | AIR      | 2025-06-01  | BOM  | LHR | AI      | BUSINESS| 7207     | 3312.06
```

**Hotel segment:**
```
Trip ID      | Traveller Email   | Seg Type | Check-In   | Check-Out  | Hotel          | Nights | Rooms | Co2e kg
TRIP-2025-001| alice@company.com | HOTEL    | 2025-05-10 | 2025-05-14 | Leela Delhi    | 4      | 1     | 124.00
TRIP-2025-002| bob@company.com   | HOTEL    | 2025-06-01 | 2025-06-05 | Heathrow Marriott| 4   | 1     | 124.00
```

**Why these choices:**
- Round trip (BLR→DEL, DEL→BLR) tests idempotency via `external_trip_id` — same trip, two segments
- International business class (BOM→LHR) tests cabin-class-weighted emission factor selection and distance calculation via ICAO haversine (7,207 km is the approximate BOM-LHR great-circle distance)
- Hotel nights for the same traveller test the `check_in_date`-based monthly assignment

### CO2e Calculations

```
Air (BLR→DEL, economy): 1,741 km × 0.153 kg CO2e/pax/km × 1.0 (no RFI) = 266.37 kg
Air (BOM→LHR, business): 7,207 km × 0.423 kg CO2e/pax/km × 1.0 = 3,048.56 kg
                          (DEFRA 2024 long-haul business = 0.423 kg/pax/km)
Hotel (4 nights): 4 nights × 1 room × 31.0 kg CO2e/room/night = 124.00 kg
```

### What Would Break in Real Deployment

1. **IATA code not in the Airport table.** A charter flight departs from a private airstrip with ICAO code but no IATA code. `distance_km` cannot be computed. The row is created with `distance_estimated = True` and `distance_km = null`, making `co2e_kg = null` and the row `FLAGGED`. Resolution requires either the admin to add the airport to `AirportLookup` or the traveller to provide the distance manually.

2. **Duplicate segments from API + CSV upload.** If Navan webhook pushes a booking in real-time AND the admin also uploads the monthly CSV export, the same segment appears twice. The current deduplication key is `external_trip_id` + `segment_type` + `travel_date`. If Navan changes the format of `trip_id` between sources, deduplication fails and double-counting occurs.

3. **Cancelled bookings.** Navan and Concur both export cancelled bookings in some report configurations. A cancelled flight was not taken and should not be counted. The `status` field in the travel export must be checked and `CANCELLED` rows dropped. If the CSV format doesn't have a status column (some don't), all booked segments are counted, overcounting emissions.

4. **Multi-city trips booked as one.** A traveller books BLR→DEL→BOM as a single multi-city booking. Navan exports this as one record with `from=BLR`, `to=BOM` and a total distance that may be straight-line BLR-BOM rather than BLR-DEL + DEL-BOM. The intermediate stop is invisible. Our `stops` field captures this, but the distance calculation still uses the straight-line approximation.

5. **Personal data masking for external auditors.** When a `LOCKED` row is exported to the external assurer, `traveller_email` should be pseudonymised. Currently, the export API returns the full email. A masking layer (hash or truncation to department-level) is needed before GA for PDPB compliance.

6. **Hotel emission factors are country-agnostic in the seed.** The seed uses 31 kg CO2e / room / night for all hotels globally. DEFRA 2024 provides regional factors (UK, Europe, US, Rest of World). A hotel in India may have a substantially different factor due to different energy mix (more coal) and older building stock. Without building-level energy audits, any hotel factor is an approximation with ±50% uncertainty.
