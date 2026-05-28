"""
apps/ingestion/management/commands/seed_demo_data.py
=====================================================
Clears all transactional data and seeds fresh, realistic demo data
for the cksdev organisation.

What is seeded:
  - 1 RawUpload per source type (SAP, UTILITY, TRAVEL)
  - 20 SAPRows  — Scope 1 Diesel / Petrol / CNG fuel procurement
  - 20 UtilityRows — Scope 2 Electricity across multiple sites
  - 20 TravelRows — Scope 3 Air / Hotel / Ground travel segments
  Total = 60 rows

Status mix (per source):
  12 APPROVED, 5 PENDING, 2 FLAGGED, 1 PARSE_FAILED

All APPROVED rows have pre-computed co2e_kg, ghg_scope, formula, etc.
(directly set, bypassing signal to keep seed fast and predictable).
Data covers FY 2025-26 (April 2025 - March 2026).

Usage:
  python manage.py seed_demo_data
"""

import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


# ── helpers ────────────────────────────────────────────────────────────────────

def rand_date(start: date, end: date) -> date:
    """Return a random date between start and end inclusive."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def fy_date(month: int, day: int) -> date:
    """Helper: produce a date in FY 2025-26 (Apr 2025 – Mar 2026)."""
    if month >= 4:
        return date(2025, month, day)
    return date(2026, month, day)


# ── Emission factor lookups (pre-loaded by load_emission_factors) ──────────────

FACTOR_DIESEL       = 2.6533   # kg CO2e / litre
FACTOR_PETROL       = 2.30
FACTOR_CNG          = 2.21     # kg CO2e / kg
FACTOR_ELEC_INDIA   = 0.710    # kg CO2e / kWh  (CEA V20, FY 2024-25)
FACTOR_FLIGHT_SHORT = 0.255    # kg CO2e / pax / km  (× RF 1.9)
FACTOR_FLIGHT_MED   = 0.195
FACTOR_FLIGHT_LONG  = 0.150
FACTOR_HOTEL        = 31.0     # kg CO2e / room / night
FACTOR_ROAD         = 0.171    # kg CO2e / km


def diesel_co2(litres):
    kg = round(litres * FACTOR_DIESEL, 2)
    return kg, f"{litres:,.2f} L x {FACTOR_DIESEL} kg CO2e/L = {kg:,.2f} kg CO2e"

def petrol_co2(litres):
    kg = round(litres * FACTOR_PETROL, 2)
    return kg, f"{litres:,.2f} L x {FACTOR_PETROL} kg CO2e/L = {kg:,.2f} kg CO2e"

def cng_co2(kg_fuel):
    kg = round(kg_fuel * FACTOR_CNG, 2)
    return kg, f"{kg_fuel:,.2f} kg x {FACTOR_CNG} kg CO2e/kg = {kg:,.2f} kg CO2e"

def elec_co2(kwh):
    kg = round(kwh * FACTOR_ELEC_INDIA, 2)
    return kg, f"{kwh:,.2f} kWh x {FACTOR_ELEC_INDIA} kg CO2e/kWh = {kg:,.2f} kg CO2e"

def flight_co2(km, pax, haul='short'):
    factor = {'short': FACTOR_FLIGHT_SHORT, 'med': FACTOR_FLIGHT_MED, 'long': FACTOR_FLIGHT_LONG}[haul]
    kg = round(km * factor * pax * 1.9, 2)  # RF=1.9
    return kg, f"{km:,.0f} km x {factor} x {pax} pax x 1.9 RF = {kg:,.2f} kg CO2e"

def hotel_co2(nights, rooms=1):
    kg = round(nights * rooms * FACTOR_HOTEL, 2)
    return kg, f"{nights} nights x {rooms} rooms x {FACTOR_HOTEL} kg CO2e = {kg:,.2f} kg CO2e"

def road_co2(km):
    kg = round(km * FACTOR_ROAD, 2)
    return kg, f"{km:,.1f} km x {FACTOR_ROAD} kg CO2e/km = {kg:,.2f} kg CO2e"


class Command(BaseCommand):
    help = "Clear all transactional data and seed realistic FY 2025-26 demo data for cksdev."

    def handle(self, *args, **options):
        from apps.organisations.models import Organisation, OrganisationMembership
        from apps.emissions.models import SAPRow, UtilityRow, TravelRow
        from apps.ingestion.models import RawUpload, AuditLog, RowComment
        from apps.ingestion.models import EmissionFactor

        # ── 1. Find the cksdev organisation ───────────────────────────────────
        try:
            org = Organisation.objects.get(slug='cksdev')
        except Organisation.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "Organisation with slug='cksdev' not found. "
                "Please create it first or check the slug."
            ))
            return

        self.stdout.write(f"Seeding data for organisation: {org.name} ({org.slug})")

        # Resolve users
        try:
            admin_user   = User.objects.get(email__iexact='adminkrish@cksdev.com')
            analyst_user = User.objects.get(email__iexact='analystkrish@cksdev.com')
            auditor_user = User.objects.get(email__iexact='auditorKrish@cksdev.com')
        except User.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"User not found: {e}"))
            return

        # Get emission factor UUIDs for audit trail
        ef_diesel = EmissionFactor.objects.filter(scope='SCOPE_1', fuel_or_activity_type='diesel', is_active=True).first()
        ef_petrol = EmissionFactor.objects.filter(scope='SCOPE_1', fuel_or_activity_type='petrol', is_active=True).first()
        ef_cng    = EmissionFactor.objects.filter(scope='SCOPE_1', fuel_or_activity_type='cng', is_active=True).first()
        ef_elec   = EmissionFactor.objects.filter(scope='SCOPE_2', fuel_or_activity_type='electricity_india', is_active=True).first()
        ef_air_s  = EmissionFactor.objects.filter(scope='SCOPE_3', fuel_or_activity_type='flight_short_haul', is_active=True).first()
        ef_air_m  = EmissionFactor.objects.filter(scope='SCOPE_3', fuel_or_activity_type='flight_medium_haul', is_active=True).first()
        ef_air_l  = EmissionFactor.objects.filter(scope='SCOPE_3', fuel_or_activity_type='flight_long_haul', is_active=True).first()
        ef_hotel  = EmissionFactor.objects.filter(scope='SCOPE_3', fuel_or_activity_type='hotel_night', is_active=True).first()
        ef_road   = EmissionFactor.objects.filter(scope='SCOPE_3', fuel_or_activity_type='ground_transport_road', is_active=True).first()

        with transaction.atomic():
            # ── 2. Delete all old transactional data ──────────────────────────
            self.stdout.write("  Deleting old row data...")
            RowComment.objects.filter(organisation=org).delete()
            AuditLog.objects.filter(organisation=org).delete()
            TravelRow.objects.filter(organisation=org).delete()
            UtilityRow.objects.filter(organisation=org).delete()
            SAPRow.objects.filter(organisation=org).delete()
            RawUpload.objects.filter(organisation=org).delete()
            self.stdout.write(self.style.WARNING("  Old data cleared."))

            # ── 3. Create RawUpload anchors ───────────────────────────────────
            ru_sap = RawUpload.objects.create(
                organisation=org,
                source_type='SAP',
                original_filename='SAP_ME2M_FY2526_Q1Q2Q3.csv',
                status='DONE',
                row_count=20,
                uploaded_by=analyst_user,
            )
            ru_util = RawUpload.objects.create(
                organisation=org,
                source_type='UTILITY',
                original_filename='Utility_Bills_FY2526_AllSites.csv',
                status='DONE',
                row_count=20,
                uploaded_by=analyst_user,
            )
            ru_travel = RawUpload.objects.create(
                organisation=org,
                source_type='TRAVEL',
                original_filename='Navan_TravelExport_FY2526.csv',
                status='DONE',
                row_count=20,
                uploaded_by=analyst_user,
            )

            # ── 4. SAP Rows (Scope 1 — Fuel Procurement) ──────────────────────
            self.stdout.write("  Creating 20 SAP rows (Scope 1)...")

            SAP_ROWS = [
                # (po, item, mat_code, mat_desc, plant, fuel_type, qty, unit, net_val, date, status)
                ('4500001001', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL01', 'diesel', 5000, 'litres', 350000, fy_date(4, 10), 'APPROVED'),
                ('4500001002', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL02', 'diesel', 3800, 'litres', 266000, fy_date(4, 22), 'APPROVED'),
                ('4500001003', '10', 'MAT-PETROL-001', 'Motor Spirit / Petrol',   'PL01', 'petrol', 2200, 'litres', 198000, fy_date(5, 5),  'APPROVED'),
                ('4500001004', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL03', 'diesel', 6100, 'litres', 427000, fy_date(5, 18), 'APPROVED'),
                ('4500001005', '10', 'MAT-CNG-001',    'Compressed Natural Gas',  'PL01', 'cng',    1200, 'kg',     84000,  fy_date(6, 2),  'APPROVED'),
                ('4500001006', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL02', 'diesel', 4400, 'litres', 308000, fy_date(6, 14), 'APPROVED'),
                ('4500001007', '10', 'MAT-PETROL-001', 'Motor Spirit / Petrol',   'PL03', 'petrol', 1800, 'litres', 162000, fy_date(7, 8),  'APPROVED'),
                ('4500001008', '10', 'MAT-CNG-001',    'Compressed Natural Gas',  'PL02', 'cng',    950,  'kg',     66500,  fy_date(7, 21), 'APPROVED'),
                ('4500001009', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL01', 'diesel', 5500, 'litres', 385000, fy_date(8, 3),  'APPROVED'),
                ('4500001010', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL03', 'diesel', 4200, 'litres', 294000, fy_date(8, 19), 'APPROVED'),
                ('4500001011', '10', 'MAT-PETROL-001', 'Motor Spirit / Petrol',   'PL01', 'petrol', 2500, 'litres', 225000, fy_date(9, 4),  'APPROVED'),
                ('4500001012', '10', 'MAT-CNG-001',    'Compressed Natural Gas',  'PL03', 'cng',    1100, 'kg',     77000,  fy_date(9, 17), 'APPROVED'),
                ('4500001013', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL02', 'diesel', 3900, 'litres', 273000, fy_date(10, 1), 'FLAGGED'),
                ('4500001014', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL01', 'diesel', 6500, 'litres', 455000, fy_date(10, 15),'APPROVED'),
                ('4500001015', '10', 'MAT-PETROL-001', 'Motor Spirit / Petrol',   'PL02', 'petrol', 2100, 'litres', 189000, fy_date(11, 6), 'APPROVED'),
                ('4500001016', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL03', 'diesel', 4800, 'litres', 336000, fy_date(11, 22),'APPROVED'),
                ('4500001017', '10', 'MAT-CNG-001',    'Compressed Natural Gas',  'PL01', 'cng',    800,  'kg',     56000,  fy_date(12, 10),'PENDING'),
                ('4500001018', '10', 'MAT-DIESEL-001', 'High-Speed Diesel (HSD)', 'PL02', 'diesel', 5200, 'litres', 364000, fy_date(1, 8),  'PENDING'),
                ('4500001019', '10', 'MAT-PETROL-001', 'Motor Spirit / Petrol',   'PL03', 'petrol', 1950, 'litres', 175500, fy_date(2, 14), 'PENDING'),
                ('4500001020', '20', 'MAT-DIESEL-002', 'High-Speed Diesel (HSD)', 'PL01', 'diesel', 7000, 'litres', 490000, fy_date(3, 2),  'PARSE_FAILED'),
            ]

            plant_names = {'PL01': 'Chennai Manufacturing Unit', 'PL02': 'Pune Assembly Plant', 'PL03': 'Mumbai Logistics Hub'}
            esg_cat_map = {'diesel': 'Fuel Combustion — Diesel', 'petrol': 'Fuel Combustion — Petrol', 'cng': 'Fuel Combustion — CNG'}
            ef_map      = {'diesel': ef_diesel, 'petrol': ef_petrol, 'cng': ef_cng}
            co2_func    = {'diesel': diesel_co2, 'petrol': petrol_co2, 'cng': cng_co2}

            for row_data in SAP_ROWS:
                po, item, mat_code, mat_desc, plant, fuel, qty, unit, net, doc_date, row_status = row_data
                ef_rec = ef_map.get(fuel)

                if row_status == 'APPROVED':
                    co2_kg, formula = co2_func[fuel](qty)
                    ghg_scope   = 'SCOPE_1'
                    ghg_cat     = esg_cat_map[fuel]
                    ef_val      = FACTOR_DIESEL if fuel == 'diesel' else (FACTOR_PETROL if fuel == 'petrol' else FACTOR_CNG)
                    ef_unit_str = 'kg CO2e / litre' if fuel != 'cng' else 'kg CO2e / kg'
                else:
                    co2_kg, formula, ghg_scope, ghg_cat, ef_val, ef_unit_str = None, None, None, None, None, None

                SAPRow.objects.create(
                    organisation      = org,
                    raw_upload        = ru_sap,
                    status            = row_status,
                    po_number         = po,
                    line_item         = item,
                    material_code     = mat_code,
                    material_description = mat_desc,
                    plant_code        = plant,
                    plant_name        = plant_names[plant],
                    vendor_id         = f'VEND-{random.randint(1000, 9999)}',
                    quantity          = Decimal(str(qty)),
                    unit_original     = unit,
                    unit_normalised   = unit,
                    net_value         = Decimal(str(net)),
                    currency          = 'INR',
                    document_date     = doc_date,
                    esg_category      = esg_cat_map[fuel],
                    co2e_kg           = Decimal(str(co2_kg)) if co2_kg else None,
                    ghg_scope         = ghg_scope,
                    ghg_category      = ghg_cat,
                    emission_factor_value  = ef_val,
                    emission_factor_unit   = ef_unit_str,
                    emission_factor_source = 'IPCC_2006',
                    emission_factor_year   = 2020,
                    emission_factor_record_id = ef_rec.id if ef_rec else None,
                    formula           = formula,
                    parse_error       = 'Duplicate PO detected — manual review required' if row_status == 'PARSE_FAILED' else '',
                    anomaly_flags     = ['MAJOR_VARIANCE'] if row_status == 'FLAGGED' else [],
                )

            self.stdout.write(self.style.SUCCESS("  SAP rows created."))

            # ── 5. Utility Rows (Scope 2 — Electricity) ───────────────────────
            self.stdout.write("  Creating 20 Utility rows (Scope 2)...")

            SITES = [
                ('ACC-001-CHN', 'MTR-CHN-001', 'Chennai Manufacturing Unit'),
                ('ACC-002-PUN', 'MTR-PUN-002', 'Pune Assembly Plant'),
                ('ACC-003-MUM', 'MTR-MUM-003', 'Mumbai Logistics Hub'),
                ('ACC-004-BLR', 'MTR-BLR-004', 'Bengaluru Tech Office'),
            ]

            UTIL_ROWS = [
                # (site_idx, billing_start, billing_end, kwh, status, doc_claimed_co2)
                (0, fy_date(4, 1),  fy_date(4, 30),  48200, 'APPROVED', None),
                (1, fy_date(4, 1),  fy_date(4, 30),  32100, 'APPROVED', None),
                (2, fy_date(4, 1),  fy_date(4, 30),  21500, 'APPROVED', None),
                (3, fy_date(4, 1),  fy_date(4, 30),  15800, 'APPROVED', None),
                (0, fy_date(5, 1),  fy_date(5, 31),  51300, 'APPROVED', None),
                (1, fy_date(5, 1),  fy_date(5, 31),  33800, 'APPROVED', None),
                (2, fy_date(5, 1),  fy_date(5, 31),  22400, 'APPROVED', None),
                (3, fy_date(5, 1),  fy_date(5, 31),  16200, 'APPROVED', None),
                (0, fy_date(6, 1),  fy_date(6, 30),  55000, 'APPROVED', None),
                (1, fy_date(6, 1),  fy_date(6, 30),  35200, 'APPROVED', None),
                (0, fy_date(7, 1),  fy_date(7, 31),  52800, 'APPROVED', 37600),   # doc claim ≈5% off → MATCH
                (1, fy_date(7, 1),  fy_date(7, 31),  34100, 'APPROVED', 28000),   # doc claim ~20% off → MAJOR_VARIANCE
                (2, fy_date(7, 1),  fy_date(7, 31),  23900, 'APPROVED', None),
                (3, fy_date(7, 1),  fy_date(7, 31),  17500, 'APPROVED', None),
                (0, fy_date(8, 1),  fy_date(8, 31),  49600, 'APPROVED', None),
                (1, fy_date(8, 1),  fy_date(8, 31),  31200, 'APPROVED', None),
                (2, fy_date(9, 1),  fy_date(9, 30),  24100, 'FLAGGED',  None),
                (3, fy_date(10, 1), fy_date(10, 31), 18300, 'PENDING',  None),
                (0, fy_date(11, 1), fy_date(11, 30), 47200, 'PENDING',  None),
                (1, fy_date(12, 1), fy_date(12, 31), 30100, 'PENDING',  None),
            ]

            for r in UTIL_ROWS:
                site_idx, b_start, b_end, kwh, row_status, doc_claimed = r
                acc, mtr, site = SITES[site_idx]
                period_month = f"{b_start.year}-{b_start.month:02d}"

                if row_status == 'APPROVED':
                    co2_kg, formula = elec_co2(kwh)
                    sys_calc = co2_kg

                    # Comparison logic
                    if doc_claimed is not None:
                        variance_pct = abs((doc_claimed - sys_calc) / sys_calc * 100)
                        if variance_pct < 5:
                            cmp_status = 'MATCH'
                        elif variance_pct < 15:
                            cmp_status = 'MINOR_VARIANCE'
                        else:
                            cmp_status = 'MAJOR_VARIANCE'
                    else:
                        doc_claimed, variance_pct, cmp_status = None, None, 'NOT_APPLICABLE'
                        sys_calc = co2_kg
                else:
                    co2_kg = formula = sys_calc = None
                    doc_claimed, variance_pct, cmp_status = None, None, None

                UtilityRow.objects.create(
                    organisation          = org,
                    raw_upload            = ru_util,
                    status                = row_status,
                    account_number        = acc,
                    meter_id              = mtr,
                    site_name             = site,
                    billing_start         = b_start,
                    billing_end           = b_end,
                    period_month          = period_month,
                    consumption_original  = Decimal(str(kwh)),
                    unit_original         = 'kWh',
                    consumption_kwh       = Decimal(str(kwh)),
                    grid_factor_used      = Decimal(str(FACTOR_ELEC_INDIA)),
                    grid_factor_vintage_year = 2024,
                    co2e_kg               = Decimal(str(co2_kg)) if co2_kg else None,
                    ghg_scope             = 'SCOPE_2' if row_status == 'APPROVED' else None,
                    ghg_category          = 'Purchased Electricity' if row_status == 'APPROVED' else None,
                    emission_factor_value = FACTOR_ELEC_INDIA if row_status == 'APPROVED' else None,
                    emission_factor_unit  = 'kg CO2e / kWh' if row_status == 'APPROVED' else None,
                    emission_factor_source= 'CEA_V20' if row_status == 'APPROVED' else None,
                    emission_factor_year  = 2024 if row_status == 'APPROVED' else None,
                    emission_factor_record_id = ef_elec.id if ef_elec and row_status == 'APPROVED' else None,
                    formula               = formula,
                    document_claimed_co2_kg  = doc_claimed,
                    system_calculated_co2_kg = sys_calc,
                    co2_variance_pct         = round(variance_pct, 2) if variance_pct else None,
                    co2_comparison_status    = cmp_status,
                    anomaly_flags         = ['MAJOR_VARIANCE'] if cmp_status == 'MAJOR_VARIANCE' else [],
                )

            self.stdout.write(self.style.SUCCESS("  Utility rows created."))

            # ── 6. Travel Rows (Scope 3) ──────────────────────────────────────
            self.stdout.write("  Creating 20 Travel rows (Scope 3)...")

            TRAVEL_ROWS = [
                # (type, description, date, status, *calc_args)
                # AIR rows
                ('AIR', 'BOM-DEL', fy_date(4, 8),  'APPROVED', 1150, 'short', 1, 'BOM', 'DEL', None, None),
                ('AIR', 'DEL-BLR', fy_date(4, 15), 'APPROVED', 1740, 'med',   1, 'DEL', 'BLR', None, None),
                ('AIR', 'BOM-SIN', fy_date(5, 3),  'APPROVED', 4400, 'long',  1, 'BOM', 'SIN', None, None),
                ('AIR', 'MAA-BOM', fy_date(5, 20), 'APPROVED',  1120, 'short', 2, 'MAA', 'BOM', None, None),
                ('AIR', 'DEL-LHR', fy_date(6, 10), 'APPROVED', 6700, 'long',  1, 'DEL', 'LHR', None, None),
                ('AIR', 'BLR-HYD', fy_date(7, 4),  'APPROVED',  500, 'short', 1, 'BLR', 'HYD', None, None),
                ('AIR', 'BOM-DXB', fy_date(7, 18), 'APPROVED', 1900, 'med',   2, 'BOM', 'DXB', None, None),
                ('AIR', 'DEL-SFO', fy_date(8, 12), 'APPROVED', 12000, 'long', 1, 'DEL', 'SFO', None, None),
                ('AIR', 'MAA-BLR', fy_date(9, 5),  'APPROVED',  290, 'short', 1, 'MAA', 'BLR', None, None),
                ('AIR', 'BOM-CCU', fy_date(9, 22), 'APPROVED', 1890, 'med',   1, 'BOM', 'CCU', None, None),
                # HOTEL rows
                ('HOTEL', 'Mumbai Taj', fy_date(4, 8),  'APPROVED', None, None, None, None, None, 2, 1),
                ('HOTEL', 'Delhi Oberoi', fy_date(4, 15), 'APPROVED', None, None, None, None, None, 3, 1),
                ('HOTEL', 'Singapore Marina Bay', fy_date(5, 3), 'APPROVED', None, None, None, None, None, 4, 1),
                ('HOTEL', 'London Marriott', fy_date(6, 10), 'APPROVED', None, None, None, None, None, 5, 2),
                ('HOTEL', 'Hyderabad Novotel', fy_date(7, 4), 'APPROVED', None, None, None, None, None, 1, 1),
                # GROUND rows
                ('GROUND', 'Mumbai Airport Transfer', fy_date(4, 8),   'APPROVED', 35,   None, None, None, None, None, None),
                ('GROUND', 'Delhi Office to Airport', fy_date(6, 10),  'APPROVED', 28,   None, None, None, None, None, None),
                ('GROUND', 'BLR Corp Office Transfer', fy_date(7, 4),  'APPROVED', 22,   None, None, None, None, None, None),
                # PENDING / FLAGGED
                ('AIR', 'BOM-DEL', fy_date(10, 15), 'PENDING',  1150, 'short', 1, 'BOM', 'DEL', None, None),
                ('HOTEL', 'Chennai ITC', fy_date(11, 5), 'FLAGGED', None, None, None, None, None, 3, 1),
            ]

            for r in TRAVEL_ROWS:
                seg_type, desc, travel_date, row_status, dist, haul, pax, dep, arr, nights, rooms = r

                # Build segment-specific fields
                seg_kwargs = {}
                co2_kg = formula = None

                if seg_type == 'AIR' and row_status == 'APPROVED':
                    co2_kg, formula = flight_co2(dist, pax or 1, haul)
                    ef_rec_travel = {'short': ef_air_s, 'med': ef_air_m, 'long': ef_air_l}[haul]
                    ef_val_travel = {'short': FACTOR_FLIGHT_SHORT, 'med': FACTOR_FLIGHT_MED, 'long': FACTOR_FLIGHT_LONG}[haul]
                    seg_kwargs = {
                        'departure_airport_code': dep,
                        'arrival_airport_code':   arr,
                        'cabin_class':            'ECONOMY',
                        'rfi_applied':            True,
                        'number_of_passengers':   pax or 1,
                        'distance_km':            Decimal(str(dist)),
                        'distance_source':        'HAVERSINE',
                        'ghg_scope':              'SCOPE_3',
                        'ghg_category':           f'Business Travel — Air ({haul.replace("med", "medium")} haul)',
                        'emission_factor_value':  ef_val_travel,
                        'emission_factor_unit':   'kg CO2e / passenger / km',
                        'emission_factor_source': 'DEFRA_2024',
                        'emission_factor_year':   2024,
                        'emission_factor_record_id': ef_rec_travel.id if ef_rec_travel else None,
                    }

                elif seg_type == 'HOTEL' and row_status == 'APPROVED':
                    co2_kg, formula = hotel_co2(nights or 1, rooms or 1)
                    seg_kwargs = {
                        'hotel_name':      desc,
                        'number_of_nights': nights or 1,
                        'number_of_rooms':  rooms or 1,
                        'check_in_date':   travel_date,
                        'check_out_date':  travel_date + timedelta(days=nights or 1),
                        'ghg_scope':       'SCOPE_3',
                        'ghg_category':    'Business Travel — Hotel Stay',
                        'emission_factor_value': FACTOR_HOTEL,
                        'emission_factor_unit':  'kg CO2e / room / night',
                        'emission_factor_source': 'DEFRA_2024',
                        'emission_factor_year':  2024,
                        'emission_factor_record_id': ef_hotel.id if ef_hotel else None,
                    }

                elif seg_type == 'GROUND' and row_status == 'APPROVED':
                    co2_kg, formula = road_co2(dist)
                    seg_kwargs = {
                        'ground_sub_type': 'TAXI',
                        'ground_provider': 'Ola/Uber',
                        'distance_km':    Decimal(str(dist)),
                        'ghg_scope':      'SCOPE_3',
                        'ghg_category':   'Business Travel — Ground (Taxi)',
                        'emission_factor_value': FACTOR_ROAD,
                        'emission_factor_unit':  'kg CO2e / km',
                        'emission_factor_source': 'DEFRA_2024',
                        'emission_factor_year':  2024,
                        'emission_factor_record_id': ef_road.id if ef_road else None,
                    }
                elif seg_type == 'AIR' and row_status != 'APPROVED':
                    seg_kwargs = {
                        'departure_airport_code': dep,
                        'arrival_airport_code':   arr,
                        'cabin_class':            'ECONOMY',
                        'number_of_passengers':   pax or 1,
                        'distance_km':            Decimal(str(dist)) if dist else None,
                    }
                elif seg_type == 'HOTEL' and row_status != 'APPROVED':
                    seg_kwargs = {
                        'hotel_name':      desc,
                        'number_of_nights': nights or 1,
                        'number_of_rooms':  rooms or 1,
                        'check_in_date':   travel_date,
                    }

                TravelRow.objects.create(
                    organisation    = org,
                    raw_upload      = ru_travel,
                    status          = row_status,
                    segment_type    = seg_type,
                    travel_date     = travel_date,
                    trip_name       = desc,
                    traveller_email = analyst_user.email,
                    booking_source  = 'NAVAN',
                    co2e_kg         = Decimal(str(co2_kg)) if co2_kg else None,
                    formula         = formula,
                    anomaly_flags   = ['FLAGGED_FOR_REVIEW'] if row_status == 'FLAGGED' else [],
                    **seg_kwargs,
                )

            self.stdout.write(self.style.SUCCESS("  Travel rows created."))

            # ── 7. Plant Lookup (WERKS codes) ────────────────────────────────
            self.stdout.write("  Creating plant lookup codes...")
            from apps.emissions.models import PlantLookup

            PlantLookup.objects.filter(organisation=org).delete()

            PLANTS = [
                # (werks, name, address, city, state, country, postal, region, type, scope, notes, active)
                ('PL01', 'Chennai Manufacturing Unit',
                 '12, Industrial Estate, Ambattur', 'Chennai', 'Tamil Nadu', 'IN', '600058',
                 'ASIA_PACIFIC', 'MANUFACTURING', 'SCOPE_1',
                 'Primary fuel-based manufacturing unit. Diesel generators + fleet.', True),

                ('PL02', 'Pune Assembly Plant',
                 'Plot 45, Pimpri-Chinchwad MIDC', 'Pune', 'Maharashtra', 'IN', '411018',
                 'ASIA_PACIFIC', 'MANUFACTURING', 'SCOPE_1',
                 'Assembly operations. Diesel + CNG fork lifts.', True),

                ('PL03', 'Mumbai Logistics Hub',
                 'Warehouse Complex, Bhiwandi', 'Mumbai', 'Maharashtra', 'IN', '421302',
                 'ASIA_PACIFIC', 'WAREHOUSE', 'SCOPE_1_2',
                 'Distribution centre. Diesel vehicles + grid electricity.', True),

                ('PL04', 'Bengaluru Tech Office',
                 '7th Floor, RMZ Ecospace, Outer Ring Road', 'Bengaluru', 'Karnataka', 'IN', '560103',
                 'ASIA_PACIFIC', 'OFFICE', 'SCOPE_2',
                 'Software & analytics team. Electricity only (Scope 2).', True),

                ('PL05', 'Delhi Regional Office',
                 'Tower B, Cyber Hub, Gurugram', 'New Delhi', 'Delhi', 'IN', '122002',
                 'ASIA_PACIFIC', 'OFFICE', 'SCOPE_2',
                 'Sales & operations HQ. Electricity only (Scope 2).', True),

                ('PL06', 'Hyderabad Technology Centre',
                 'HITEC City, Madhapur', 'Hyderabad', 'Telangana', 'IN', '500081',
                 'ASIA_PACIFIC', 'DATA_CENTRE', 'SCOPE_2',
                 'Tier 2 data centre. High electricity consumption.', True),

                ('DE01', 'Berlin European HQ',
                 'Unter den Linden 25', 'Berlin', None, 'DE', '10117',
                 'EUROPE', 'OFFICE', 'SCOPE_2',
                 'European operations HQ. Fully electric.', True),

                ('DE02', 'Munich Manufacturing Plant',
                 'Industriestrasse 88, Garching', 'Munich', None, 'DE', '85748',
                 'EUROPE', 'MANUFACTURING', 'SCOPE_1',
                 'Automotive components. Natural gas heating + diesel fleet.', True),

                ('GB01', 'London UK Office',
                 '22 Bishopsgate, City of London', 'London', None, 'GB', 'EC2N 4BQ',
                 'EUROPE', 'OFFICE', 'SCOPE_2',
                 'UK & EMEA sales office. Grid electricity.', True),

                ('AE01', 'Dubai Middle East Office',
                 'Level 18, Index Tower, DIFC', 'Dubai', None, 'AE', '00000',
                 'MIDDLE_EAST', 'OFFICE', 'SCOPE_2',
                 'Middle East & Africa regional office.', True),

                ('US01', 'New York North America HQ',
                 '1 World Trade Center, Suite 8500', 'New York', 'NY', 'US', '10007',
                 'NORTH_AMERICA', 'OFFICE', 'SCOPE_2',
                 'North America headquarters. Grid electricity.', True),

                ('OLD1', 'Pune Plant (Decommissioned)',
                 'Old Industrial Area, Hadapsar', 'Pune', 'Maharashtra', 'IN', '411028',
                 'ASIA_PACIFIC', 'MANUFACTURING', 'SCOPE_1',
                 'Decommissioned in FY 2023-24. Retained for historical data traceability.', False),
            ]

            plant_count = 0
            for p in PLANTS:
                (werks, name, address, city, state, country, postal,
                 region, ptype, scope, notes, active) = p
                PlantLookup.objects.get_or_create(
                    organisation=org,
                    werks_code=werks,
                    defaults=dict(
                        plant_name   = name,
                        address_line = address,
                        city         = city,
                        state        = state,
                        country      = country,
                        postal_code  = postal,
                        region       = region,
                        plant_type   = ptype,
                        default_scope= scope,
                        notes        = notes,
                        is_active    = active,
                        added_by     = admin_user,
                    )
                )
                plant_count += 1

            self.stdout.write(self.style.SUCCESS(f"  {plant_count} plant codes created."))

            # ── 8. Summary ────────────────────────────────────────────────────
            sap_count    = SAPRow.objects.filter(organisation=org).count()
            util_count   = UtilityRow.objects.filter(organisation=org).count()
            travel_count = TravelRow.objects.filter(organisation=org).count()
            pl_count     = PlantLookup.objects.filter(organisation=org).count()

            self.stdout.write(self.style.SUCCESS(
                f"\nSeed complete for [{org.name}]:\n"
                f"  SAP rows    : {sap_count}\n"
                f"  Utility rows: {util_count}\n"
                f"  Travel rows : {travel_count}\n"
                f"  Plant codes : {pl_count}\n"
                f"  TOTAL rows  : {sap_count + util_count + travel_count}"
            ))
