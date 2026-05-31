# MODEL.md — Data Model

```
┌─ TL;DR ──────────────────────────────────────────────────────────┐
│ Multi-tenant Django ORM with row-level tenant isolation.         │
│ Every row belongs to one Organisation; scope is auto-assigned    │
│ by parser type (SAP→S1, Utility→S2, Travel→S3).                 │
│ Biggest risk: missing tenant FK on a new model leaks all data.   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 1 · FULL ENTITY RELATIONSHIP DIAGRAM

```mermaid
erDiagram

    %% ── CORE ──────────────────────────────────────────
    Organisation {
        uuid id PK
        string name
        string slug
        datetime created_at
    }
    TenantUser {
        uuid id PK
        uuid organisation_id FK
        uuid user_id FK
        string role
        bool is_active
    }
    User {
        int id PK
        string username
        string email
    }

    %% ── REFERENCE ─────────────────────────────────────
    EmissionFactor {
        uuid id PK
        string source_type
        string ghg_scope
        string fuel_type
        string country_code
        decimal factor_value
        string unit
        string source_name
        string source_version
        int validity_year
        datetime locked_at
    }
    Airport {
        int id PK
        string iata_code
        string icao_code
        string name
        decimal latitude
        decimal longitude
        string country_code
    }

    %% ── INGESTION ─────────────────────────────────────
    IngestionBatch {
        uuid id PK
        uuid organisation_id FK
        uuid uploaded_by FK
        string source_type
        string original_filename
        string status
        int total_rows
        int parsed_rows
        int failed_rows
        datetime created_at
    }
    SAPRow {
        uuid id PK
        uuid organisation_id FK
        uuid raw_upload_id FK
        string plant_code
        string material_description
        string esg_category
        decimal quantity
        string unit_original
        string unit_normalised
        decimal co2e_kg
        uuid emission_factor_id FK
        string ghg_scope
        string status
        datetime document_date
        datetime ingested_at
        uuid ingested_by FK
        datetime last_edited_at
        uuid last_edited_by FK
        string edit_reason
        string source_type
    }
    UtilityRow {
        uuid id PK
        uuid organisation_id FK
        uuid raw_upload_id FK
        string meter_id
        string site_name
        date billing_start
        date billing_end
        int period_month
        decimal consumption_kwh
        decimal co2e_kg
        uuid emission_factor_id FK
        string ghg_scope
        string status
        datetime ingested_at
    }
    TravelRow {
        uuid id PK
        uuid organisation_id FK
        uuid raw_upload_id FK
        string segment_type
        string departure_airport_code
        string arrival_airport_code
        uuid departure_airport_id FK
        uuid arrival_airport_id FK
        decimal distance_km
        string cabin_class
        string traveller_email
        decimal co2e_kg
        uuid emission_factor_id FK
        string ghg_scope
        string status
        datetime ingested_at
    }

    %% ── AUDIT ─────────────────────────────────────────
    AuditLog {
        uuid id PK
        uuid organisation_id FK
        uuid row_id
        string row_type
        string action
        uuid performed_by FK
        jsonb payload
        datetime created_at
    }
    RowComment {
        uuid id PK
        uuid organisation_id FK
        uuid row_id
        string row_type
        uuid author FK
        string body
        bool is_finding
        bool resolved
        datetime created_at
    }

    %% ── RELATIONSHIPS ─────────────────────────────────
    Organisation     ||--o{ TenantUser      : "has members"
    Organisation     ||--o{ SAPRow          : "owns"
    Organisation     ||--o{ UtilityRow      : "owns"
    Organisation     ||--o{ TravelRow       : "owns"
    Organisation     ||--o{ IngestionBatch  : "owns"
    Organisation     ||--o{ AuditLog        : "scoped to"
    Organisation     ||--o{ RowComment      : "scoped to"
    User             ||--o{ TenantUser      : "identity"
    IngestionBatch   ||--o{ SAPRow          : "produced"
    IngestionBatch   ||--o{ UtilityRow      : "produced"
    IngestionBatch   ||--o{ TravelRow       : "produced"
    EmissionFactor   ||--o{ SAPRow          : "applied to"
    EmissionFactor   ||--o{ UtilityRow      : "applied to"
    EmissionFactor   ||--o{ TravelRow       : "applied to"
    Airport          ||--o{ TravelRow       : "departure"
    Airport          ||--o{ TravelRow       : "arrival"
```

---

## 2 · MULTI-TENANCY ARCHITECTURE

```mermaid
graph TD
    subgraph REQUEST["Incoming Request"]
        JWT["JWT Token\n(user_id)"]
    end

    subgraph RESOLVE["Tenant Resolution"]
        JWT --> TU["TenantUser lookup\n(user_id + org claim)"]
        TU --> ROLE["Role extracted\nADMIN / ANALYST / AUDITOR"]
    end

    subgraph PERMISSION["Permission Check"]
        ROLE --> P1{"Is tenant\nmember?"}
        P1 -- "✗ No" --> HTTP403["403 Forbidden\nno data returned"]
        P1 -- "✓ Yes" --> P2{"Role has\npermission?"}
        P2 -- "✗ No" --> HTTP403
        P2 -- "✓ Yes" --> QS["Queryset filter\n.filter(organisation=org)"]
    end

    subgraph DATA["Data Layer"]
        QS --> ROWS["Only this org's rows\nreturned"]
    end

    style HTTP403 fill:#ef4444,color:#fff
    style ROWS fill:#22c55e,color:#fff
```

**RBAC Hierarchy:**

| Role | Upload | Review | Approve/Reject | Lock | Admin |
|------|--------|--------|----------------|------|-------|
| ADMIN | ✓ | ✓ | ✓ | ✓ | ✓ |
| ANALYST | ✓ | ✓ | ✓ | ✗ | ✗ |
| AUDITOR | ✗ | ✓ (read) | ✗ | ✓ | ✗ |
| VIEWER | ✗ | ✓ (read) | ✗ | ✗ | ✗ |

---

## 3 · SCOPE 1/2/3 CATEGORISATION FLOW

```mermaid
flowchart TD
    UPLOAD["File Upload / API Call\n(IngestionBatch created)"] --> DETECT

    DETECT{"Source type\ndetected?"}
    DETECT -- "SAP flat file\n.txt / .csv" --> SAP_PARSE
    DETECT -- "Utility PDF\n(OCR)" --> UTIL_PARSE
    DETECT -- "Travel JSON\n(Navan API)" --> TRAV_PARSE

    SAP_PARSE["SAP Parser\n· Split columns\n· Normalise MEINS unit\n· Match WERKS → PlantLookup"]
    SAP_PARSE --> SAP_SCOPE["ghg_scope = SCOPE_1\nghg_category = STATIONARY_COMBUSTION\nor MOBILE_COMBUSTION"]
    SAP_SCOPE --> SAP_CO2["CO2e = quantity_litres × IPCC_factor\n(e.g. diesel × 2.6533 kgCO2e/L)"]

    UTIL_PARSE["Utility Parser\n· OCR page text\n· Extract kWh, meter_id\n· Parse billing dates"]
    UTIL_PARSE --> UTIL_SCOPE["ghg_scope = SCOPE_2\nghg_category = PURCHASED_ELECTRICITY"]
    UTIL_SCOPE --> UTIL_CO2["CO2e = kWh × 0.710\n(CEA FY24-25, location-based)"]

    TRAV_PARSE["Travel Parser\n· Parse segment JSON\n· Lookup IATA → Airport coords\n· Haversine distance calc"]
    TRAV_PARSE --> TRAV_SCOPE["ghg_scope = SCOPE_3\nghg_category = BUSINESS_TRAVEL"]
    TRAV_SCOPE --> TRAV_CO2["CO2e = distance_km × class_factor × RF\n(DEFRA/ICAO, RF=1.9)"]

    SAP_CO2 --> STATUS
    UTIL_CO2 --> STATUS
    TRAV_CO2 --> STATUS

    STATUS{"Parse\nsuccess?"}
    STATUS -- "✓" --> PENDING["status = PENDING\nAuditLog: INGESTED + CALCULATED"]
    STATUS -- "✗" --> FAILED["status = PARSE_FAILED\nparse_error = reason\nAuditLog: FAILED"]

    style PENDING fill:#22c55e,color:#fff
    style FAILED fill:#ef4444,color:#fff
```

---

## 4 · SOURCE-OF-TRUTH TRACKING

**Fields on every row model:**

| Field | Purpose | Editable? |
|---|---|---|
| `source_type` | SAP / UTILITY / TRAVEL | ✗ Immutable |
| `source_file` | original filename from `IngestionBatch` | ✗ Immutable |
| `ingested_at` | creation timestamp | ✗ Immutable |
| `ingested_by` | user FK (null if system trigger) | ✗ Immutable |
| `parsed_by_version` | parser semver string e.g. `sap-parser@1.4.2` | ✗ Immutable |
| `emission_factor_id` | FK to `EmissionFactor` — factor locked at calc time | ✗ Immutable |
| `last_edited_at` | null if never manually edited | ✓ System-set |
| `last_edited_by` | user FK | ✓ System-set |
| `edit_reason` | required free-text if row is edited | ✓ Analyst |
| `is_system_derived` | True if co2e_kg was auto-calculated | ✓ System-set |

**Lifecycle Sequence:**

```mermaid
sequenceDiagram
    participant U as Analyst
    participant API as Ingestion API
    participant DB as Database
    participant AL as AuditLog

    U->>API: POST /upload (file)
    API->>DB: IngestionBatch.create()
    API->>DB: Row.create(status=PENDING)
    API->>AL: INGESTED {file, row_count, timestamp}

    API->>DB: co2e_kg = quantity × factor
    API->>AL: CALCULATED {factor_id, factor_value, formula}

    U->>API: PATCH /row/{id} (edit value)
    API->>DB: Row.update(value, last_edited_by, edit_reason)
    API->>AL: EDITED {field, old_value, new_value, reason}

    U->>API: POST /approve {row_id}
    API->>DB: Row.update(status=APPROVED)
    API->>AL: APPROVED {approver, timestamp}

    Note over AL: AuditLog is append-only.<br/>No UPDATE or DELETE ever.
```

---

## 5 · UNIT NORMALISATION FLOWCHART

```mermaid
flowchart TD
    IN["Raw MEINS value\nfrom SAP row"] --> UPPER["upper().strip()"]

    UPPER --> L{"L, LITRE,\nLTR, LITR?"}
    UPPER --> GAL{"GAL, GALLON,\nGALLONE?"}
    UPPER --> KG{"KG, KGS,\nKILOGRAM?"}
    UPPER --> M3{"M3, M³,\nCBM?"}
    UPPER --> MT{"MT, TO,\nTONNE, TON?"}
    UPPER --> UNK{"No match"}

    L   -- "store as-is" --> LITRES["unit_normalised = L\nquantity_litres = MENGE"]
    GAL -- "× 3.785411784" --> LITRES
    KG  -- "store as-is" --> KGS["unit_normalised = KG\nquantity_kg = MENGE"]
    M3  -- "store as-is" --> M3OUT["unit_normalised = M3\nquantity_m3 = MENGE"]
    MT  -- "× 1000" --> KGS

    UNK --> FAIL["status = PARSE_FAILED\nparse_error = 'Unknown unit: [X]'\nAuditLog: FAILED action\nRow excluded from CO2 totals"]

    LITRES  --> CO2["CO2e = normalised_qty × IPCC_factor"]
    KGS     --> CO2
    M3OUT   --> CO2

    style FAIL fill:#ef4444,color:#fff
    style CO2 fill:#22c55e,color:#fff
```

> Analyst path after FAILED row: download error report → fix source file → re-upload. No silent best-guess is ever attempted.

---

## 6 · AI CHATBOT TEXT-TO-SQL FLOW

```mermaid
flowchart TD
    USER["User Question\n(e.g. 'Show total Scope 1')"] --> INTENT["intent_classifier"]
    
    INTENT -- "data_query" --> SCHEMA["schema_retriever\n(Fetch DB Schema)"]
    SCHEMA --> SQLGEN["sql_generator\n(LLM creates SQL)"]
    
    SQLGEN --> VAL["sql_validator_node\n(AST & Security Check)"]
    VAL -- "Invalid" --> SQLGEN
    VAL -- "Valid" --> EXEC["sql_executor\n(Run readonly on DB)"]
    
    EXEC --> FMT["response_formatter\n(Format as Text/Table)"]
    INTENT -- "explain/clarify" --> FMT
    
    FMT --> OUT["output_classifier\n(Determine UI element)"]
    OUT --> UI["Frontend UI"]
    
    style EXEC fill:#22c55e,color:#fff
    style VAL fill:#eab308,color:#fff
```
