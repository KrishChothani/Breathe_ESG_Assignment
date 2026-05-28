# DECISIONS.md — Decisions & Ambiguities

```
┌─ TL;DR ──────────────────────────────────────────────────────────┐
│ 12 decisions made under ambiguity, each with an explicit         │
│ alternative and a failure mode.                                  │
│ Most impactful: emission factors in DB not code (D10) —          │
│ enables zero-downtime factor updates without redeployment.       │
│ Biggest open question: is Scope 3 travel blocking or optional?   │
└──────────────────────────────────────────────────────────────────┘
```

---

## SOURCE DECISIONS

---

```
┌─ DECISION D1: SAP Integration Method ────────────────────────────┐
│ Chose:     Flat file upload (.txt / .csv from MB51/ME2M)         │
│ Over:      OData API, RFC/BAPI call, IDoc stream, SAP BTP        │
│ Because:   Every SAP customer can export MB51 without BASIS      │
│            team involvement or firewall changes.                 │
│ Would ask PM: Does the client have SAP BASIS team capacity to    │
│            expose an OData gateway in scope?                     │
│ Breaks if: Analyst forgets to export and uploads stale file;     │
│            no automated freshness check exists.                  │
└──────────────────────────────────────────────────────────────────┘
```

```
┌─ DECISION D2: Utility Bill Ingestion Mode ───────────────────────┐
│ Chose:     PDF OCR (AI-assisted extraction of kWh + dates)       │
│ Over:      Portal CSV download, direct utility API, manual entry │
│ Because:   MSEDCL/MSEB does not publish a public API; portal CSV │
│            format changes quarterly without notice.              │
│ Would ask PM: Is the client willing to grant portal scraping     │
│            credentials for automated monthly pull?              │
│ Breaks if: MSEDCL redesigns PDF layout — regex/prompt will      │
│            silently extract wrong kWh until re-tested.           │
└──────────────────────────────────────────────────────────────────┘
```

```
┌─ DECISION D3: Travel API Schema ─────────────────────────────────┐
│ Chose:     Navan API JSON schema (expense + trip segments)        │
│ Over:      Concur Expense v4, Expensify API, generic CSV upload  │
│ Because:   Navan is the client's stated TMC; schema was built    │
│            directly from their Swagger/OpenAPI spec.             │
│ Would ask PM: Are there employees booking outside Navan          │
│            (personal cards, local travel agents)?               │
│ Breaks if: Client switches TMC — entire parser needs rebuild;    │
│            no adapter layer exists yet.                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## SCOPE DECISIONS

---

```
┌─ DECISION D4: SAP Data Subset ───────────────────────────────────┐
│ Chose:     Fuel rows only (diesel, petrol, CNG, LPG, HFO)        │
│ Over:      Full procurement scope (raw materials, packaging, MRO) │
│ Because:   Scope 1 requires only direct combustion fuels;        │
│            materials = Scope 3 cat.1 requiring spend-based model.│
│ Would ask PM: Is Scope 3 category 1 (purchased goods) in scope   │
│            for this disclosure period?                           │
│ Breaks if: Procurement team uploads full MB51 export including   │
│            non-fuel rows — system flags them PARSE_FAILED if     │
│            ESG category mapping is missing.                      │
└──────────────────────────────────────────────────────────────────┘
```

```
┌─ DECISION D5: Utility Subset ────────────────────────────────────┐
│ Chose:     Electricity consumption only (kWh → CEA factor)        │
│ Over:      Piped gas (Scope 1), water, steam (Scope 2 cat.)      │
│ Because:   CEA publishes only electricity grid factors; gas       │
│            billing is billed in SCM/MCM which needs PNGRB data. │
│ Would ask PM: Does the client have piped natural gas at any      │
│            facility? (Changes Scope 1, not Scope 2.)            │
│ Breaks if: Client uploads a gas bill PDF — OCR extracts numbers  │
│            but there is no gas EmissionFactor row → CO2e = null. │
└──────────────────────────────────────────────────────────────────┘
```

```
┌─ DECISION D6: Travel Subset ─────────────────────────────────────┐
│ Chose:     Flights, hotels, ground transport (taxi/rail/car)      │
│ Over:      Visa fees, meal expenses, per diem, conference fees   │
│ Because:   Only physical travel segments have published emission  │
│            factors; ancillary costs are Scope 3 cat.6 spend-based│
│ Would ask PM: Is spend-based Scope 3 category 6 (employee        │
│            commute) in scope for this inventory boundary?        │
│ Breaks if: Navan returns expense type = "MEAL" — parser drops    │
│            the row silently (status = SKIPPED, not FAILED).      │
└──────────────────────────────────────────────────────────────────┘
```

---

## DATA QUALITY DECISIONS

---

```
┌─ DECISION D7: Anomaly Detection Method ──────────────────────────┐
│ Chose:     Statistical spike: row > 2 std dev of 30-day rolling  │
│            mean for same plant/meter → status = FLAGGED          │
│ Over:      Cross-source validation, ML anomaly model, none       │
│ Because:   Rolling mean needs no training data; works from day 1 │
│            with as few as 5 prior rows.                          │
│ Would ask PM: Is cross-source validation (e.g. compare SAP       │
│            diesel qty vs fuel card statement) required?          │
│ Breaks if: A genuine step-change in consumption (new factory)    │
│            triggers mass false-positive flags — analyst workload │
│            spike for 30 days until baseline resets.              │
└──────────────────────────────────────────────────────────────────┘
```

```
┌─ DECISION D8: CO2 Variance Threshold ────────────────────────────┐
│ Chose:     15% variance between system-calculated and claimed     │
│            CO2 triggers auto-flag                                │
│ Over:      10% (too sensitive for rounding differences),         │
│            20% (too loose for material misstatement detection)   │
│ Because:   DEFRA guidance uses 15% materiality for energy        │
│            management systems; aligns with ISO 50001.            │
│ Would ask PM: What materiality threshold does the assurance      │
│            firm use for this client's disclosure?                │
│ Breaks if: Client uses a non-standard factor (e.g. supplier      │
│            EPD value) that always differs by >15% from our DB.  │
└──────────────────────────────────────────────────────────────────┘
```

```
┌─ DECISION D9: Unknown Unit Handling ─────────────────────────────┐
│ Chose:     Fail-hard: status = PARSE_FAILED, analyst must        │
│            re-upload corrected file                              │
│ Over:      Best-guess (infer from context), skip silently,       │
│            default to litres                                     │
│ Because:   A wrong unit silently alters CO2e — litres vs m³ =   │
│            ~800× difference for diesel; audit risk is too high.  │
│ Would ask PM: Is there an approved unit lookup table from the    │
│            client's SAP config we can preload?                   │
│ Breaks if: High-volume uploads with non-standard units create    │
│            analyst bottleneck — no bulk re-map tool exists yet.  │
└──────────────────────────────────────────────────────────────────┘
```

---

## ARCHITECTURE DECISIONS

---

```
┌─ DECISION D10: Emission Factor Storage ──────────────────────────┐
│ Chose:     EmissionFactor model in DB with validity_year,        │
│            source_name, source_version, locked_at UUID           │
│ Over:      Hardcoded constants in Python, YAML config file,      │
│            environment variables                                 │
│ Because:   Factors change annually (CEA, DEFRA); DB allows       │
│            zero-downtime updates without redeployment.           │
│ Would ask PM: Should users be able to add custom factors         │
│            (e.g. renewable energy certificate factors)?          │
│ Breaks if: A factor is added with wrong validity_year — all      │
│            historical rows recalculate incorrectly on next run.  │
└──────────────────────────────────────────────────────────────────┘
```

```
┌─ DECISION D11: AuditLog Immutability ────────────────────────────┐
│ Chose:     Append-only AuditLog model; no UPDATE or DELETE ever  │
│            permitted at ORM or DB level                          │
│ Over:      Soft-delete (deleted_at flag), versioned records,     │
│            event sourcing with snapshots                         │
│ Because:   SEBI BRSR external assurance requires complete,       │
│            tamper-evident trail — soft-delete is reversible.     │
│ Would ask PM: Is blockchain anchoring of the audit hash          │
│            required for the assurance firm's standards?          │
│ Breaks if: DB admin runs a direct DELETE query — no application- │
│            level protection against superuser DB access.         │
└──────────────────────────────────────────────────────────────────┘
```

```
┌─ DECISION D12: Airport Coordinate Source ────────────────────────┐
│ Chose:     OurAirports.com dataset (70k+ airports, CC0 license)  │
│            loaded to Airport model via management command        │
│ Over:      Google Maps API, OpenCage, FlightAware, runtime calls │
│ Because:   Runtime API calls add latency + cost per row; IATA    │
│            codes are stable — no need for live lookup.           │
│ Would ask PM: Are private/charter airports (no IATA code) in     │
│            scope? (They are absent from OurAirports dataset.)   │
│ Breaks if: Employee flies to a new airport not yet in dataset —  │
│            TravelRow.departure_airport_id = null, distance_km =  │
│            null, CO2e = null, status = FLAGGED.                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## WHAT I WOULD ASK THE PM

| # | Question | Why It Changes the Architecture |
|---|----------|--------------------------------|
| Q1 | Is Scope 3 travel mandatory or comply-or-explain for this disclosure period? | If optional → travel ingestion is a nice-to-have; if mandatory → it blocks BRSR submission |
| Q2 | Does the client have electricity consumption outside India (overseas offices)? | India CEA factor only; overseas offices need UK DEFRA / US EPA eGRID factors — EmissionFactor table supports this but rows don't exist |
| Q3 | Will the assurance firm accept location-based Scope 2 or do they require market-based (RECs/PPAs)? | Market-based requires a completely separate REC tracking model and dual-calculation path |
| Q4 | Is the renewable energy mix of the client's grid operators known (state-level CEA data)? | State-level factors already vary 3×; using national average could over/understate by 40%+ |
| Q5 | Is automated monthly ingestion required or is manual analyst upload acceptable? | Manual upload = current architecture; automated = needs SAP OData connector + MSEDCL scraper + Navan webhook — 3 separate integrations |
