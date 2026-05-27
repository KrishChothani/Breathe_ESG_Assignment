"""
seed_data.py — BreatheESG complete demo data seed (multi-tenant edition)
=========================================================================
Creates 2 organisations with isolated data. Verifies tenant isolation at end.

Usage:
    python manage.py seed_data
    python manage.py seed_data --flush   # wipe all seeded rows first
"""

import random
from datetime import date, timedelta, datetime
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify


def ok(label, n):
    print(f"  [+]  {label:<45} {n} rows")


class Command(BaseCommand):
    help = "Seed BreatheESG with multi-tenant demo data (2 organisations)"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true",
                            help="Delete all seeded row data before re-seeding.")

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.users.models import User
        from apps.organisations.models import Organisation, OrganisationMembership
        from apps.ingestion.models import RawUpload
        from apps.emissions.models import (
            SAPRow, UtilityRow, TravelRow,
            PlantLookup, GridEmissionFactor, AirportLookup,
            TravelEmissionFactor,
        )
        from apps.review.models import ReviewAction

        self.stdout.write(self.style.MIGRATE_HEADING("\n[SEED] BreatheESG Multi-Tenant Seed Data\n"))

        if options["flush"]:
            self.stdout.write("  Flushing existing row data...")
            ReviewAction.objects.all().delete()
            TravelRow.objects.all().delete()
            UtilityRow.objects.all().delete()
            SAPRow.objects.all().delete()
            RawUpload.objects.all().delete()
            TravelEmissionFactor.objects.all().delete()
            AirportLookup.objects.all().delete()
            GridEmissionFactor.objects.all().delete()
            PlantLookup.objects.all().delete()
            OrganisationMembership.objects.all().delete()
            Organisation.objects.all().delete()
            self.stdout.write("  [OK] Flushed.\n")

        # ── 1. ORGANISATIONS ──────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("1 / 10  Organisations"))

        acme, _ = Organisation.objects.get_or_create(
            slug="acme",
            defaults=dict(
                name="Acme Manufacturing Ltd",
                industry="Manufacturing",
                country="IN",
                subscription_plan="ENTERPRISE",
                is_active=True,
            ),
        )
        beta, _ = Organisation.objects.get_or_create(
            slug="beta",
            defaults=dict(
                name="Beta Logistics GmbH",
                industry="Logistics",
                country="DE",
                subscription_plan="PRO",
                is_active=True,
            ),
        )
        ok("Organisations", 2)

        # ── 2. USERS + MEMBERSHIPS ────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("2 / 10  Users & Memberships"))

        def make_user(email, first, last, role, password="BreatheESG@2026!"):
            u, created = User.objects.get_or_create(
                email=email,
                defaults=dict(
                    username=email,      # username == email for simplejwt login
                    first_name=first, last_name=last,
                    role=role, is_staff=(role == 'ADMIN'),
                ),
            )
            # Always reset password and username (idempotent on re-run)
            u.username = email
            u.set_password(password)
            u.save(update_fields=['username', 'password'])
            return u

        # ── Acme demo users (password: BreatheESG@2026!) ──────────────────────
        acme_admin   = make_user("admin@acme.com",   "Arjun",  "Mehta",   "ADMIN")
        acme_analyst = make_user("analyst@acme.com", "Priya",  "Sharma",  "ANALYST")
        acme_auditor = make_user("auditor@acme.com", "Sophie", "Laurent", "AUDITOR")
        # Beta demo users
        beta_admin   = make_user("admin@beta.com",   "Klaus",  "Mueller", "ADMIN")
        beta_analyst = make_user("analyst@beta.com", "Rahul",  "Verma",   "ANALYST")

        # ── Krish personal accounts (password: Krish@259) ─────────────────────
        krish_admin   = make_user("krishadmin@gmail.com",   "Krish", "Admin",   "ADMIN",   password="Krish@259")
        krish_analyst = make_user("krishanalyst@gmail.com", "Krish", "Analyst", "ANALYST", password="Krish@259")
        krish_auditor = make_user("krishaditor@gmail.com",  "Krish", "Auditor", "AUDITOR", password="Krish@259")

        # Memberships
        for user, org, role in [
            (acme_admin,    acme, "ADMIN"),
            (acme_analyst,  acme, "ANALYST"),
            (acme_auditor,  acme, "AUDITOR"),
            (beta_admin,    beta, "ADMIN"),
            (beta_analyst,  beta, "ANALYST"),
            # Krish accounts — all see Acme data
            (krish_admin,   acme, "ADMIN"),
            (krish_analyst, acme, "ANALYST"),
            (krish_auditor, acme, "AUDITOR"),
        ]:
            OrganisationMembership.objects.get_or_create(
                organisation=org, user=user, defaults=dict(role=role, is_active=True)
            )

        ok("Users", 8)
        ok("Memberships", 8)

        # ── 3. GRID EMISSION FACTORS (Acme) ───────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("3 / 10  Grid Emission Factors"))
        gef_data = [
            ("IN", 2025, Decimal("0.708200"), "CEA India 2025"),
            ("IN", 2024, Decimal("0.716000"), "CEA India 2024"),
            ("DE", 2025, Decimal("0.364900"), "UBA Germany 2025"),
            ("GB", 2025, Decimal("0.233000"), "DESNZ UK 2025"),
            ("US", 2025, Decimal("0.386000"), "EPA eGRID 2025"),
            ("AE", 2025, Decimal("0.450000"), "IEA UAE 2025"),
        ]
        gefs = {}
        for country, year, factor, source in gef_data:
            gef, _ = GridEmissionFactor.objects.get_or_create(
                organisation=acme, country=country, year=year,
                defaults=dict(factor_kg_per_kwh=factor, source=source),
            )
            gefs[country] = gef
        ok("Grid Emission Factors (Acme)", len(gefs))

        # ── 4. PLANT LOOKUPS (Acme) ───────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("4 / 10  Plant Lookups (WERKS)"))
        plant_data = [
            dict(werks_code="1000",   plant_name="Mumbai Main Manufacturing",   city="Mumbai",    state="Maharashtra", country="IN", region="ASIA_PACIFIC",  plant_type="MANUFACTURING", default_scope="SCOPE_1"),
            dict(werks_code="1001",   plant_name="Mumbai Warehouse & Dispatch", city="Mumbai",    state="Maharashtra", country="IN", region="ASIA_PACIFIC",  plant_type="WAREHOUSE",     default_scope="SCOPE_1_2"),
            dict(werks_code="2001",   plant_name="Delhi Regional Office",       city="New Delhi", state="Delhi",       country="IN", region="ASIA_PACIFIC",  plant_type="OFFICE",        default_scope="SCOPE_2"),
            dict(werks_code="IN_HYD", plant_name="Hyderabad Technology Centre", city="Hyderabad", state="Telangana",   country="IN", region="ASIA_PACIFIC",  plant_type="DATA_CENTRE",   default_scope="SCOPE_2"),
            dict(werks_code="DE01",   plant_name="Berlin European HQ",          city="Berlin",    state="Berlin",      country="DE", region="EUROPE",        plant_type="OFFICE",        default_scope="SCOPE_2"),
            dict(werks_code="DE02",   plant_name="Munich Manufacturing Plant",  city="Munich",    state="Bavaria",     country="DE", region="EUROPE",        plant_type="MANUFACTURING", default_scope="SCOPE_1"),
            dict(werks_code="GB01",   plant_name="London UK Office",            city="London",    state=None,          country="GB", region="EUROPE",        plant_type="OFFICE",        default_scope="SCOPE_2"),
            dict(werks_code="US01",   plant_name="New York North America HQ",   city="New York",  state="New York",    country="US", region="NORTH_AMERICA", plant_type="OFFICE",        default_scope="SCOPE_2"),
            dict(werks_code="AE01",   plant_name="Dubai Middle East Office",    city="Dubai",     state=None,          country="AE", region="MIDDLE_EAST",   plant_type="OFFICE",        default_scope="SCOPE_2"),
            dict(werks_code="OLD1",   plant_name="Pune Plant (Decommissioned)", city="Pune",      state="Maharashtra", country="IN", region="ASIA_PACIFIC",  plant_type="MANUFACTURING", default_scope="SCOPE_1", is_active=False),
            # These two have NO lookup entry — appear in Unresolved WERKS tab
            # (left intentionally absent)
        ]
        plants = {}
        for pd in plant_data:
            is_active = pd.pop("is_active", True)
            plant, _ = PlantLookup.objects.get_or_create(
                organisation=acme, werks_code=pd["werks_code"],
                defaults=dict(
                    **pd, is_active=is_active,
                    added_by=acme_admin,
                    grid_emission_factor=gefs.get(pd["country"]),
                ),
            )
            plants[pd["werks_code"]] = plant
        ok("Plant Lookups (Acme)", len(plants))

        # ── 5. AIRPORTS (Acme) ────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("5 / 10  Airport Lookups"))
        airport_data = [
            ("BOM", "Chhatrapati Shivaji International",       "Mumbai",      "IN",  Decimal("19.088700"),  Decimal("72.867900")),
            ("DEL", "Indira Gandhi International",             "New Delhi",   "IN",  Decimal("28.556600"),  Decimal("77.100200")),
            ("HYD", "Rajiv Gandhi International",              "Hyderabad",   "IN",  Decimal("17.231100"),  Decimal("78.429800")),
            ("FRA", "Frankfurt Airport",                       "Frankfurt",   "DE",  Decimal("50.033300"),  Decimal("8.570500")),
            ("MUC", "Munich Airport",                          "Munich",      "DE",  Decimal("48.353800"),  Decimal("11.786100")),
            ("LHR", "Heathrow Airport",                        "London",      "GB",  Decimal("51.477500"),  Decimal("-0.461400")),
            ("JFK", "John F. Kennedy International",           "New York",    "US",  Decimal("40.641800"),  Decimal("-73.778100")),
            ("DXB", "Dubai International",                     "Dubai",       "AE",  Decimal("25.252800"),  Decimal("55.364400")),
            ("SIN", "Singapore Changi",                        "Singapore",   "SG",  Decimal("1.359200"),   Decimal("103.989400")),
        ]
        airports = {}
        for iata, name, city, country, lat, lon in airport_data:
            ap, _ = AirportLookup.objects.get_or_create(
                organisation=acme, iata=iata,
                defaults=dict(name=name, city=city, country=country, lat=lat, lon=lon),
            )
            airports[iata] = ap
        ok("Airports (Acme)", len(airports))

        # ── 6. TRAVEL EMISSION FACTORS (Acme) ────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("6 / 10  Travel Emission Factors"))
        tef_data = [
            dict(category="AIR", cabin_class="ECONOMY",         factor_kg_per_unit=Decimal("0.151700"), unit_description="kgCO2e/pax-km", source="DEFRA 2025", vintage_year=2025, rfi_included=True),
            dict(category="AIR", cabin_class="PREMIUM_ECONOMY", factor_kg_per_unit=Decimal("0.227500"), unit_description="kgCO2e/pax-km", source="DEFRA 2025", vintage_year=2025, rfi_included=True),
            dict(category="AIR", cabin_class="BUSINESS",        factor_kg_per_unit=Decimal("0.428800"), unit_description="kgCO2e/pax-km", source="DEFRA 2025", vintage_year=2025, rfi_included=True),
            dict(category="AIR", cabin_class="FIRST",           factor_kg_per_unit=Decimal("0.607200"), unit_description="kgCO2e/pax-km", source="DEFRA 2025", vintage_year=2025, rfi_included=True),
            dict(category="HOTEL", region="IN",     factor_kg_per_unit=Decimal("18.300000"), unit_description="kgCO2e/room-night", source="HCMI 2024", vintage_year=2024),
            dict(category="HOTEL", region="DE",     factor_kg_per_unit=Decimal("9.700000"),  unit_description="kgCO2e/room-night", source="HCMI 2024", vintage_year=2024),
            dict(category="HOTEL", region="GB",     factor_kg_per_unit=Decimal("8.200000"),  unit_description="kgCO2e/room-night", source="HCMI 2024", vintage_year=2024),
            dict(category="HOTEL", region="US",     factor_kg_per_unit=Decimal("11.500000"), unit_description="kgCO2e/room-night", source="HCMI 2024", vintage_year=2024),
            dict(category="CAR", fuel_type="PETROL",  car_category="MEDIUM", factor_kg_per_unit=Decimal("0.170500"), unit_description="kgCO2e/km", source="DEFRA 2025", vintage_year=2025),
            dict(category="CAR", fuel_type="DIESEL",  car_category="MEDIUM", factor_kg_per_unit=Decimal("0.163900"), unit_description="kgCO2e/km", source="DEFRA 2025", vintage_year=2025),
            dict(category="RAIL", rail_carrier="DB",     factor_kg_per_unit=Decimal("0.006300"), unit_description="kgCO2e/pax-km", source="DB 2025",      vintage_year=2025),
            dict(category="RAIL", region="IN",           factor_kg_per_unit=Decimal("0.012200"), unit_description="kgCO2e/pax-km", source="Indian Railways 2025", vintage_year=2025),
            dict(category="GROUND_TRANSPORT", sub_type="TAXI", factor_kg_per_unit=Decimal("0.149000"), unit_description="kgCO2e/km", source="DEFRA 2025", vintage_year=2025),
        ]
        tefs = []
        for td in tef_data:
            tef, _ = TravelEmissionFactor.objects.get_or_create(
                organisation=acme,
                category    = td["category"],
                cabin_class = td.get("cabin_class"),
                sub_type    = td.get("sub_type"),
                fuel_type   = td.get("fuel_type"),
                car_category= td.get("car_category"),
                region      = td.get("region"),
                rail_carrier= td.get("rail_carrier"),
                defaults    = dict(
                    factor_kg_per_unit=td["factor_kg_per_unit"],
                    unit_description  =td.get("unit_description", ""),
                    source            =td.get("source", ""),
                    vintage_year      =td.get("vintage_year"),
                    rfi_included      =td.get("rfi_included", False),
                ),
            )
            tefs.append(tef)
        ok("Travel Emission Factors (Acme)", len(tefs))

        # ── 7. RAW UPLOADS (Acme) ─────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("7 / 10  Raw Uploads"))
        upload_specs = [
            ("sap_q1",  "SAP",     acme_analyst, "SAP_ME2M_Q1_2026_Mumbai.csv",   "DONE", 480),
            ("sap_q2",  "SAP",     acme_analyst, "SAP_ME2M_Q2_2026_Mumbai.csv",   "DONE", 520),
            ("sap_de",  "SAP",     acme_analyst, "SAP_MB51_2026_Germany.csv",     "DONE", 240),
            ("util_mum","UTILITY", acme_analyst, "TATA_Power_Jan_Mar_2026.csv",   "DONE",  36),
            ("util_del","UTILITY", acme_analyst, "BSES_Delhi_Q1_2026.csv",        "DONE",  24),
            ("util_de", "UTILITY", acme_analyst, "ENBW_Munich_Q1_2026.csv",       "DONE",  12),
            ("travel_q1","TRAVEL", acme_analyst, "Navan_API_Q1_2026_sync.json",   "DONE", 180),
            ("travel_q2","TRAVEL", acme_analyst, "Navan_API_Q2_2026_sync.json",   "DONE", 200),
            ("sap_pend","SAP",     acme_analyst, "SAP_ME2M_Q3_2026_Draft.csv",    "PROCESSING", None),
        ]
        uploads = {}
        for key, source, user, fname, stat, count in upload_specs:
            up, _ = RawUpload.objects.get_or_create(
                organisation=acme, original_filename=fname,
                defaults=dict(source_type=source, status=stat, row_count=count, uploaded_by=user),
            )
            uploads[key] = up
        ok("Raw Uploads (Acme)", len(uploads))

        # ── 8. SAP ROWS (Acme) ────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("8 / 10  SAP / Utility / Travel Rows"))
        sap_templates = [
            ("4500012301","10","MAT-HSD", "High Speed Diesel",        "1000", "VENDOR001", Decimal("45000"), "LT",  Decimal("2812500"), "INR", "Fuel - Diesel",            "APPROVED", Decimal("119025.00")),
            ("4500012302","10","MAT-LPG", "Liquefied Petroleum Gas",  "1000", "VENDOR002", Decimal("8500"),  "KG",  Decimal("595000"),  "INR", "Fuel - LPG",               "APPROVED", Decimal("25211.00")),
            ("4500012303","10","MAT-NG",  "Natural Gas",              "1001", "VENDOR003", Decimal("12000"), "M3",  Decimal("480000"),  "INR", "Fuel - Natural Gas",       "APPROVED", Decimal("26376.00")),
            ("4500012304","10","MAT-COOL","Industrial Coolant R-22",  "1000", "VENDOR004", Decimal("200"),   "KG",  Decimal("160000"),  "INR", "Refrigerants",             "FLAGGED",  Decimal("4120.00")),
            ("4500012305","10","MAT-PACK","Corrugated Packaging",     "1001", "VENDOR005", Decimal("50000"), "KG",  Decimal("500000"),  "INR", "Packaging Materials",      "PENDING",  None),
            ("4500012306","10","MAT-STEE","Steel Coils HR Grade",     "1000", "VENDOR006", Decimal("25000"), "KG",  Decimal("1875000"), "INR", "Raw Materials - Metals",   "LOCKED",   Decimal("55000.00")),
            ("4500012307","10","MAT-HSD", "High Speed Diesel",        "2001", "VENDOR001", Decimal("5000"),  "LT",  Decimal("312500"),  "INR", "Fuel - Diesel",            "APPROVED", Decimal("13225.00")),
            ("4500012308","10","MAT-ELEC","Electrical Grid Purchase",  "IN_HYD","VENDOR007",Decimal("280000"),"KWH",Decimal("2240000"), "INR", "Purchased Electricity",    "APPROVED", Decimal("198296.00")),
            ("4500012309","10","MAT-HSD", "Diesel Germany",           "DE02", "VENDOR-DE1",Decimal("18000"), "LT",  Decimal("27000"),   "EUR", "Fuel - Diesel",            "APPROVED", Decimal("47628.00")),
            ("4500012310","10","MAT-ELEC","Electricity Germany",      "DE01", "VENDOR-DE3",Decimal("95000"), "KWH", Decimal("14250"),   "EUR", "Purchased Electricity",    "LOCKED",   Decimal("34665.50")),
            ("4500012311","10","MAT-HSD", "High Speed Diesel Q2",     "1000", "VENDOR001", Decimal("22000"), "LT",  Decimal("1375000"), "INR", "Fuel - Diesel",            "LOCKED",   Decimal("58234.00")),
            ("4500012312","10","MAT-WELD","Welding Gas (Acetylene)",  "1000", "VENDOR009", Decimal("1500"),  "M3",  Decimal("225000"),  "INR", "Industrial Gases",         "REJECTED", Decimal("5100.00")),
            # Unresolved WERKS codes (no PlantLookup entry)
            ("4500012313","10","MAT-HSD", "Diesel",                   "9999", "VENDOR011", Decimal("3000"),  "LT",  Decimal("187500"),  "INR", "Fuel - Diesel",            "PENDING",  None),
            ("4500012314","10","MAT-CHEM","Chemical Y",               "UNKN", "VENDOR012", Decimal("500"),   "KG",  Decimal("75000"),   "INR", "Industrial Chemicals",     "PENDING",  None),
        ]

        upload_map = {
            "1000":"sap_q1","1001":"sap_q1","2001":"sap_q1","IN_HYD":"sap_q2",
            "DE01":"sap_de","DE02":"sap_de","9999":"sap_pend","UNKN":"sap_pend",
        }
        base_date = date(2026, 1, 15)
        sap_rows  = []
        for i, (po, li, mc, md, pc, vi, qty, unit, nv, curr, esg, stat, co2e) in enumerate(sap_templates):
            plant_entry = plants.get(pc)
            row, _ = SAPRow.objects.get_or_create(
                organisation=acme, po_number=po, line_item=li,
                defaults=dict(
                    raw_upload=uploads[upload_map.get(pc, "sap_q1")],
                    material_code=mc, material_description=md,
                    plant_code=pc, plant_name=plant_entry.plant_name if plant_entry else "",
                    vendor_id=vi, quantity=qty, unit_original=unit, unit_normalised=unit,
                    net_value=nv, currency=curr,
                    document_date=base_date + timedelta(days=i * 7),
                    esg_category=esg, status=stat, co2e_kg=co2e,
                ),
            )
            sap_rows.append(row)
        ok("SAP Rows (Acme)", len(sap_rows))

        # ── Utility rows ──────────────────────────────────────────────────────
        utility_specs = [
            ("TATA-MUM-001","MTR-MUM-A1","Mumbai Factory Block A","2026-01",date(2026,1,1),date(2026,1,31),Decimal("285000"),"KWH",Decimal("285000"),Decimal("0.7082"),2025,"APPROVED",Decimal("201837.00")),
            ("TATA-MUM-001","MTR-MUM-A1","Mumbai Factory Block A","2026-02",date(2026,2,1),date(2026,2,28),Decimal("271000"),"KWH",Decimal("271000"),Decimal("0.7082"),2025,"APPROVED",Decimal("191922.20")),
            ("TATA-MUM-001","MTR-MUM-A1","Mumbai Factory Block A","2026-03",date(2026,3,1),date(2026,3,31),Decimal("298000"),"KWH",Decimal("298000"),Decimal("0.7082"),2025,"LOCKED",  Decimal("211043.60")),
            ("TATA-MUM-002","MTR-MUM-WH","Mumbai Warehouse",      "2026-01",date(2026,1,1),date(2026,1,31),Decimal("54000"), "KWH",Decimal("54000"), Decimal("0.7082"),2025,"APPROVED",Decimal("38242.80")),
            ("TATA-MUM-002","MTR-MUM-WH","Mumbai Warehouse",      "2026-02",date(2026,2,1),date(2026,2,28),Decimal("51000"), "KWH",Decimal("51000"), Decimal("0.7082"),2025,"PENDING", None),
            ("BSES-DEL-001","MTR-DEL-01","Delhi Office",          "2026-01",date(2026,1,1),date(2026,1,31),Decimal("42000"), "KWH",Decimal("42000"), Decimal("0.7082"),2025,"APPROVED",Decimal("29744.40")),
            ("BSES-DEL-001","MTR-DEL-01","Delhi Office",          "2026-02",date(2026,2,1),date(2026,2,28),Decimal("39500"), "KWH",Decimal("39500"), Decimal("0.7082"),2025,"APPROVED",Decimal("27973.90")),
            ("BSES-DEL-001","MTR-DEL-01","Delhi Office",          "2026-03",date(2026,3,1),date(2026,3,31),Decimal("44500"), "KWH",Decimal("44500"), Decimal("0.7082"),2025,"LOCKED",  Decimal("31514.90")),
            ("ENBW-MUC-001","MTR-DE-MUC","Munich Manufacturing",  "2026-01",date(2026,1,1),date(2026,1,31),Decimal("195000"),"KWH",Decimal("195000"),Decimal("0.3649"),2025,"APPROVED",Decimal("71155.50")),
            ("ENBW-MUC-001","MTR-DE-MUC","Munich Manufacturing",  "2026-02",date(2026,2,1),date(2026,2,28),Decimal("188000"),"KWH",Decimal("188000"),Decimal("0.3649"),2025,"APPROVED",Decimal("68601.20")),
        ]
        util_map = {"MUM": uploads["util_mum"], "DEL": uploads["util_del"], "DE": uploads["util_de"]}
        util_rows = []
        for acct, meter, site, period, bstart, bend, co, unit, ckwh, gf, gfy, stat, co2e in utility_specs:
            key = "MUM" if "MUM" in meter else ("DEL" if "DEL" in meter else "DE")
            row, _ = UtilityRow.objects.get_or_create(
                organisation=acme, account_number=acct, meter_id=meter, period_month=period,
                defaults=dict(raw_upload=util_map[key], site_name=site, billing_start=bstart,
                              billing_end=bend, consumption_original=co, unit_original=unit,
                              consumption_kwh=ckwh, grid_factor_used=gf, grid_factor_vintage_year=gfy,
                              status=stat, co2e_kg=co2e),
            )
            util_rows.append(row)
        ok("Utility Rows (Acme)", len(util_rows))

        # ── Travel rows ───────────────────────────────────────────────────────
        travel_specs = [
            dict(navan_trip_id="NVN-2026-00101", trip_name="Mumbai-London Client Visit",
                 traveller_email="analyst@acme.com", segment_type="AIR", travel_date=date(2026,2,5),
                 departure_airport_code="BOM", arrival_airport_code="LHR",
                 airline_carrier="AI", flight_number="AI131", cabin_class="BUSINESS",
                 stops=0, rfi_applied=True, distance_km=Decimal("7186.00"),
                 cost_amount=Decimal("185000.00"), cost_currency="INR",
                 emission_factor_used=Decimal("0.428800"), emission_factor_source="DEFRA 2025",
                 co2e_kg=Decimal("3082.92"), status="APPROVED", number_of_passengers=1),
            dict(navan_trip_id="NVN-2026-00101", trip_name="Mumbai-London Client Visit",
                 traveller_email="analyst@acme.com", segment_type="HOTEL", travel_date=date(2026,2,5),
                 hotel_name="The Savoy", hotel_chain_code="LHW", hotel_country="GB",
                 check_in_date=date(2026,2,5), check_out_date=date(2026,2,10),
                 number_of_nights=5, number_of_rooms=1,
                 cost_amount=Decimal("62500.00"), cost_currency="INR",
                 emission_factor_used=Decimal("8.200000"), emission_factor_source="HCMI 2024",
                 co2e_kg=Decimal("41.00"), status="APPROVED"),
            dict(navan_trip_id="NVN-2026-00215", trip_name="Frankfurt Summit",
                 traveller_email="analyst@acme.com", segment_type="AIR", travel_date=date(2026,3,12),
                 departure_airport_code="BOM", arrival_airport_code="FRA",
                 airline_carrier="LH", flight_number="LH761", cabin_class="ECONOMY",
                 stops=0, rfi_applied=True, distance_km=Decimal("6272.00"),
                 cost_amount=Decimal("78000.00"), cost_currency="INR",
                 emission_factor_used=Decimal("0.151700"), emission_factor_source="DEFRA 2025",
                 co2e_kg=Decimal("951.48"), status="LOCKED", number_of_passengers=1),
            dict(navan_trip_id="NVN-2026-00215", trip_name="Frankfurt Summit",
                 traveller_email="analyst@acme.com", segment_type="RAIL", travel_date=date(2026,3,13),
                 rail_carrier="DB", departure_station="Frankfurt Hbf", arrival_station="Munchen Hbf",
                 rail_class="2nd", distance_km=Decimal("400.00"),
                 cost_amount=Decimal("4800.00"), cost_currency="INR",
                 emission_factor_used=Decimal("0.006300"), emission_factor_source="DB 2025",
                 co2e_kg=Decimal("2.52"), status="LOCKED"),
            dict(navan_trip_id="NVN-2026-00330", trip_name="New York Annual Review",
                 traveller_email="analyst@acme.com", segment_type="AIR", travel_date=date(2026,4,8),
                 departure_airport_code="DEL", arrival_airport_code="JFK",
                 airline_carrier="AI", flight_number="AI101", cabin_class="PREMIUM_ECONOMY",
                 stops=0, rfi_applied=True, distance_km=Decimal("11764.00"),
                 cost_amount=Decimal("220000.00"), cost_currency="INR",
                 emission_factor_used=Decimal("0.227500"), emission_factor_source="DEFRA 2025",
                 co2e_kg=Decimal("2676.31"), status="APPROVED", number_of_passengers=1),
        ]
        travel_rows = []
        for ts in travel_specs:
            stat    = ts.pop("status")
            co2e_kg = ts.pop("co2e_kg")
            row, _  = TravelRow.objects.get_or_create(
                organisation=acme,
                navan_trip_id=ts["navan_trip_id"],
                segment_type=ts["segment_type"],
                travel_date=ts.get("travel_date"),
                departure_airport_code=ts.get("departure_airport_code"),
                arrival_airport_code=ts.get("arrival_airport_code"),
                departure_station=ts.get("departure_station"),
                arrival_station=ts.get("arrival_station"),
                defaults=dict(raw_upload=uploads["travel_q1"], status=stat, co2e_kg=co2e_kg, **ts),
            )
            travel_rows.append(row)
        ok("Travel Rows (Acme)", len(travel_rows))

        # ── 9. REVIEW ACTIONS (Acme) ──────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("9 / 10  Review Actions"))
        sap_ct    = ContentType.objects.get_for_model(SAPRow)
        util_ct   = ContentType.objects.get_for_model(UtilityRow)
        travel_ct = ContentType.objects.get_for_model(TravelRow)

        review_specs = [
            (sap_ct,    sap_rows[0],    acme_analyst, "APPROVE", "Fuel quantity verified against tank log."),
            (sap_ct,    sap_rows[1],    acme_analyst, "APPROVE", "LPG consumption within expected range."),
            (sap_ct,    sap_rows[2],    acme_analyst, "APPROVE", "Natural gas reading confirmed."),
            (sap_ct,    sap_rows[3],    acme_analyst, "FLAG",    "R-22 refrigerant - need to verify GWP factor."),
            (sap_ct,    sap_rows[5],    acme_analyst, "APPROVE", "Steel procurement verified."),
            (sap_ct,    sap_rows[5],    acme_admin,   "LOCK",    "Locked for Q1 audit."),
            (sap_ct,    sap_rows[9],    acme_analyst, "APPROVE", "Berlin electricity verified."),
            (sap_ct,    sap_rows[9],    acme_admin,   "LOCK",    "Locked for DE audit."),
            (sap_ct,    sap_rows[11],   acme_analyst, "REJECT",  "Incorrect material code - resubmit with MAT-WELD-ACE."),
            (util_ct,   util_rows[0],   acme_analyst, "APPROVE", "Jan meter reading verified with TATA Power invoice."),
            (util_ct,   util_rows[1],   acme_analyst, "APPROVE", "Feb reading verified."),
            (util_ct,   util_rows[2],   acme_admin,   "LOCK",    "Locked for Q1 audit."),
            (util_ct,   util_rows[5],   acme_analyst, "APPROVE", "Delhi Jan reading OK."),
            (util_ct,   util_rows[6],   acme_analyst, "APPROVE", "Delhi Feb reading OK."),
            (travel_ct, travel_rows[0], acme_analyst, "APPROVE", "BOM-LHR Business class. RFI applied."),
            (travel_ct, travel_rows[1], acme_analyst, "APPROVE", "London hotel 5 nights confirmed."),
            (travel_ct, travel_rows[2], acme_analyst, "APPROVE", "FRA flight verified."),
            (travel_ct, travel_rows[2], acme_admin,   "LOCK",    "Locked for Q1 travel audit."),
            (travel_ct, travel_rows[4], acme_analyst, "APPROVE", "DEL-JFK premium economy confirmed."),
        ]
        review_count = 0
        for ct, row_obj, analyst, action, note in review_specs:
            ra, created = ReviewAction.objects.get_or_create(
                row_content_type=ct, row_object_id=row_obj.id,
                action=action, analyst=analyst, defaults=dict(note=note),
            )
            if created:
                review_count += 1
        ok("Review Actions (Acme)", review_count)

        # ── 10. TENANT ISOLATION VERIFICATION ────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("10 / 10  Tenant Isolation Verification"))

        beta_sap     = SAPRow.objects.filter(organisation=beta).count()
        beta_utility = UtilityRow.objects.filter(organisation=beta).count()
        beta_travel  = TravelRow.objects.filter(organisation=beta).count()
        beta_plants  = PlantLookup.objects.filter(organisation=beta).count()
        beta_uploads = RawUpload.objects.filter(organisation=beta).count()

        if beta_sap == 0 and beta_utility == 0 and beta_travel == 0 and beta_plants == 0 and beta_uploads == 0:
            self.stdout.write(self.style.SUCCESS("  [PASS] Tenant isolation verified — Beta sees ZERO rows from Acme data."))
        else:
            self.stdout.write(self.style.ERROR(
                f"  [FAIL] Isolation breach! Beta sees: SAP={beta_sap} Utility={beta_utility} "
                f"Travel={beta_travel} Plants={beta_plants} Uploads={beta_uploads}"
            ))

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 58))
        self.stdout.write(self.style.SUCCESS("  Seed complete! Multi-Tenant Summary:"))
        self.stdout.write(self.style.SUCCESS("=" * 58))
        self.stdout.write(f"  Organisations       : 2 (Acme + Beta)")
        self.stdout.write(f"  Users               : 5 (3 Acme, 2 Beta)")
        self.stdout.write(f"  Grid EF             : {len(gefs)}")
        self.stdout.write(f"  Plant Lookups       : {len(plants)}")
        self.stdout.write(f"  Airports            : {len(airports)}")
        self.stdout.write(f"  Travel EF           : {len(tefs)}")
        self.stdout.write(f"  Raw Uploads         : {len(uploads)}")
        self.stdout.write(f"  SAP Rows            : {len(sap_rows)} (2 with unknown WERKS -> Unresolved tab)")
        self.stdout.write(f"  Utility Rows        : {len(util_rows)}")
        self.stdout.write(f"  Travel Rows         : {len(travel_rows)}")
        self.stdout.write(f"  Review Actions      : {review_count}")
        self.stdout.write("")
        self.stdout.write("  Login credentials (all users, password: BreatheESG@2026!):")
        self.stdout.write("    admin@acme.com   | analyst@acme.com | auditor@acme.com")
        self.stdout.write("    admin@beta.com   | analyst@beta.com")
        self.stdout.write(self.style.SUCCESS("=" * 58))
