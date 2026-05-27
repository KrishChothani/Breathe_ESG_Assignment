# Architectural Decisions Log

This document captures key architectural and technical decisions made during the development of the ESG Ingestion Platform.

## 1. SAP Flat File Integration (Scope 1 & 2)

**Decision:**
Ingest SAP purchasing and material data via standard flat-file exports (ME2M / MB51 CSV or TXT formats) rather than integrating directly with SAP via BAPI/RFC calls.

**Alternatives considered:**
- Direct SAP integration via BAPI/RFC (using libraries like PyRFC).
- OData API integration via SAP NetWeaver Gateway.

**Why this:**
- Flat files drastically reduce the security and networking overhead required to connect to on-premise SAP environments.
- Most corporate IT departments are much more comfortable setting up a scheduled background job to export a CSV to a secure SFTP server or cloud bucket than they are opening up API endpoints to third-party tools.
- It decouples the ESG platform from the specific SAP ERP version or custom Z-tables, as long as the exported columns match the expected schema.

**Tradeoffs:**
- Data is asynchronous and processed in batches, meaning emissions data is not real-time.
- Potential parsing fragility if SAP users change their layout configurations or locale formats (e.g., German number formatting `1.000,00` vs English `1,000.00`).

---

## 2. PDF OCR for Utility Bills (Scope 2)

**Decision:**
Utilize an OCR (Optical Character Recognition) based pipeline to extract consumption data (kWh) from utility bill PDFs rather than requiring users to manually enter data or strictly relying on utility provider APIs.

**Alternatives considered:**
- Manual data entry forms.
- Direct integrations with individual utility provider APIs.
- EDI (Electronic Data Interchange) formats.

**Why this:**
- The utility market is highly fragmented; integrating with hundreds of individual provider APIs is unscalable for a growing ESG platform.
- Users already receive PDFs from their providers. Uploading them in bulk is a low-friction user experience.
- Combining OCR with a "Review Dashboard" (Human-in-the-Loop) ensures data accuracy while still providing high automation.

**Tradeoffs:**
- OCR accuracy is never 100%. Template variations from utility providers can cause extraction failures, requiring human intervention.
- OCR extraction can be computationally expensive or incur third-party API costs depending on the OCR engine used (e.g., AWS Textract or Google Cloud DocumentAI).

---

## 3. Concur JSON for Travel Data (Scope 3)

**Decision:**
Standardize the ingestion of business travel data using a normalized JSON payload format modeled after the Concur / Navan API schemas.

**Alternatives considered:**
- Parsing travel itinerary emails.
- Ingesting raw CSV exports from travel management companies.
- Direct scraping of travel portals.

**Why this:**
- JSON payloads from modern travel APIs are highly structured and strictly typed, minimizing parsing errors compared to CSVs or emails.
- Standardizing around the schema of industry leaders (like Concur) ensures the platform is ready to integrate out-of-the-box with the majority of large enterprise clients.
- It allows for rich metadata extraction (e.g., exact origin/destination IATA codes, cabin classes, car rental fuel types) critical for accurate Scope 3 emissions calculations.

**Tradeoffs:**
- Requires clients who don't use Concur or Navan to map their internal travel data into our expected JSON schema.
- The schema is complex and hierarchical (trips containing multiple segments), requiring more sophisticated backend parsing logic than flat data.

---

## 4. Haversine Formula vs. Geocoding API for Flight Distances

**Decision:**
OurAirports CSV loaded into local DB over runtime geocoding APIs. We calculate flight distances using the mathematical Haversine formula based on a database lookup of IATA airport coordinates (`Airport` model), falling back to this when `distance_km` is absent from the travel payload.

**Alternatives considered:**
- Google Maps Geocoding API, OpenCage, hardcoded dict
- Using a spatial database extension like PostGIS to calculate distances dynamically.

**Why this:**
- CC0 licensed, 70k+ airports, zero runtime API calls, no rate limits, works fully offline. Loaded once at deploy time via management command.
- The Haversine formula is highly accurate for calculating great-circle distances over the Earth's surface, which perfectly aligns with the standard GHG Protocol methodologies for flight emissions.

**Tradeoffs:**
- Dataset requires periodic manual refresh. IATA codes occasionally change or are reassigned — production would schedule a monthly re-sync from ourairports.com.
