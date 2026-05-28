"""
apps/ingestion/management/commands/load_emission_factors.py
===========================================================
Idempotent command that seeds all official GHG emission factors
into the EmissionFactor registry table.

Sources:
  SCOPE 1: IPCC 2006 Guidelines + India GHG Program + GHG Protocol
  SCOPE 2: CEA CO2 Baseline Database Version 20.0 (India)
  SCOPE 3: DEFRA 2024 / ICAO Carbon Emissions Calculator

Usage:
  python manage.py load_emission_factors

Safe to re-run: existing records are updated if values changed;
older FY versions are preserved for historical accuracy.
"""

from django.core.management.base import BaseCommand
from apps.ingestion.models import EmissionFactor


FACTORS = [
    # ══════════════════════════════════════════════════════════════
    # SCOPE 2 — ELECTRICITY (India, CEA CO2 Baseline Database V20)
    # ══════════════════════════════════════════════════════════════
    {
        'scope':               'SCOPE_2',
        'fuel_or_activity_type': 'electricity_india',
        'factor_value':        0.710,
        'factor_unit':         'kg CO2e / kWh',
        'source_name':         'CEA_V20',
        'source_version':      'Version 20.0',
        'valid_from_fy':       '2024-25',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'CEA CO2 Baseline Database V20.0, FY 2024-25. '
                               'Location-based weighted average. '
                               'SEBI BRSR Core Scope 2 mandatory disclosure factor.',
    },
    {
        'scope':               'SCOPE_2',
        'fuel_or_activity_type': 'electricity_india',
        'factor_value':        0.727,
        'factor_unit':         'kg CO2e / kWh',
        'source_name':         'CEA_V20',
        'source_version':      'Version 19.0',
        'valid_from_fy':       '2023-24',
        'valid_to_fy':         '2024-24',
        'country_code':        'IN',
        'is_active':           False,
        'notes':               'CEA CO2 Baseline Database V19.0, FY 2023-24. Historical factor.',
    },
    {
        'scope':               'SCOPE_2',
        'fuel_or_activity_type': 'electricity_india',
        'factor_value':        0.716,
        'factor_unit':         'kg CO2e / kWh',
        'source_name':         'CEA_V20',
        'source_version':      'Version 18.0',
        'valid_from_fy':       '2022-23',
        'valid_to_fy':         '2023-23',
        'country_code':        'IN',
        'is_active':           False,
        'notes':               'CEA CO2 Baseline Database V18.0, FY 2022-23. Historical factor.',
    },

    # ══════════════════════════════════════════════════════════════
    # SCOPE 1 — FUEL COMBUSTION
    # Source: IPCC 2006 Guidelines + GHG Protocol cross-sector tools
    # ══════════════════════════════════════════════════════════════
    {
        'scope':               'SCOPE_1',
        'fuel_or_activity_type': 'diesel',
        'factor_value':        2.6533,
        'factor_unit':         'kg CO2e / litre',
        'source_name':         'IPCC_2006',
        'source_version':      '2006 IPCC Guidelines, Volume 2',
        'valid_from_fy':       '2020-21',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Diesel (Gas Oil). NCV × EF. GHG Protocol cross-sector tool aligned.',
    },
    {
        'scope':               'SCOPE_1',
        'fuel_or_activity_type': 'petrol',
        'factor_value':        2.30,
        'factor_unit':         'kg CO2e / litre',
        'source_name':         'IPCC_2006',
        'source_version':      '2006 IPCC Guidelines, Volume 2',
        'valid_from_fy':       '2020-21',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Motor Gasoline / Petrol. IPCC 2006 default.',
    },
    {
        'scope':               'SCOPE_1',
        'fuel_or_activity_type': 'cng',
        'factor_value':        2.21,
        'factor_unit':         'kg CO2e / kg',
        'source_name':         'INDIA_GHG',
        'source_version':      'India GHG Program 2015',
        'valid_from_fy':       '2020-21',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Compressed Natural Gas. India GHG Program sector guide.',
    },
    {
        'scope':               'SCOPE_1',
        'fuel_or_activity_type': 'lpg',
        'factor_value':        2.983,
        'factor_unit':         'kg CO2e / kg',
        'source_name':         'IPCC_2006',
        'source_version':      '2006 IPCC Guidelines, Volume 2',
        'valid_from_fy':       '2020-21',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Liquefied Petroleum Gas (LPG). IPCC 2006 default.',
    },
    {
        'scope':               'SCOPE_1',
        'fuel_or_activity_type': 'natural_gas',
        'factor_value':        1.9141,
        'factor_unit':         'kg CO2e / m³',
        'source_name':         'IPCC_2006',
        'source_version':      '2006 IPCC Guidelines, Volume 2',
        'valid_from_fy':       '2020-21',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Natural Gas. Based on default NCV and emission factor.',
    },
    {
        'scope':               'SCOPE_1',
        'fuel_or_activity_type': 'coal',
        'factor_value':        2274.69,
        'factor_unit':         'kg CO2e / tonne',
        'source_name':         'IPCC_2006',
        'source_version':      '2006 IPCC Guidelines, Volume 2 — Indian sub-bituminous',
        'valid_from_fy':       '2020-21',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Indian sub-bituminous coal. IPCC 2006 Tier 1. '
                               'For Indian power plants use Ministry of Power specific factors if available.',
    },
    {
        'scope':               'SCOPE_1',
        'fuel_or_activity_type': 'furnace_oil',
        'factor_value':        3.15,
        'factor_unit':         'kg CO2e / litre',
        'source_name':         'IPCC_2006',
        'source_version':      '2006 IPCC Guidelines, Volume 2',
        'valid_from_fy':       '2020-21',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Residual Fuel Oil / Furnace Oil. IPCC 2006 default.',
    },

    # ══════════════════════════════════════════════════════════════
    # SCOPE 3 — BUSINESS TRAVEL
    # Source: DEFRA 2024 / ICAO Carbon Emissions Calculator
    # ══════════════════════════════════════════════════════════════
    {
        'scope':               'SCOPE_3',
        'fuel_or_activity_type': 'flight_short_haul',
        'factor_value':        0.255,
        'factor_unit':         'kg CO2e / passenger / km',
        'source_name':         'DEFRA_2024',
        'source_version':      'DEFRA / DESNZ 2024 Conversion Factors',
        'valid_from_fy':       '2024-25',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Short-haul flights < 1500 km. '
                               'Radiative forcing factor of 1.9x applied separately in engine.',
    },
    {
        'scope':               'SCOPE_3',
        'fuel_or_activity_type': 'flight_medium_haul',
        'factor_value':        0.195,
        'factor_unit':         'kg CO2e / passenger / km',
        'source_name':         'DEFRA_2024',
        'source_version':      'DEFRA / DESNZ 2024 Conversion Factors',
        'valid_from_fy':       '2024-25',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Medium-haul flights 1500–4000 km. RF factor applied separately.',
    },
    {
        'scope':               'SCOPE_3',
        'fuel_or_activity_type': 'flight_long_haul',
        'factor_value':        0.150,
        'factor_unit':         'kg CO2e / passenger / km',
        'source_name':         'DEFRA_2024',
        'source_version':      'DEFRA / DESNZ 2024 Conversion Factors',
        'valid_from_fy':       '2024-25',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Long-haul flights > 4000 km. RF factor 1.9x applied separately.',
    },
    {
        'scope':               'SCOPE_3',
        'fuel_or_activity_type': 'hotel_night',
        'factor_value':        31.0,
        'factor_unit':         'kg CO2e / room / night',
        'source_name':         'DEFRA_2024',
        'source_version':      'DEFRA / DESNZ 2024 Conversion Factors',
        'valid_from_fy':       '2024-25',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Hotel stays. Average global factor per room per night.',
    },
    {
        'scope':               'SCOPE_3',
        'fuel_or_activity_type': 'ground_transport_road',
        'factor_value':        0.171,
        'factor_unit':         'kg CO2e / km',
        'source_name':         'DEFRA_2024',
        'source_version':      'DEFRA / DESNZ 2024 Conversion Factors',
        'valid_from_fy':       '2024-25',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Ground transport — taxi/cab/car. Per km.',
    },
    {
        'scope':               'SCOPE_3',
        'fuel_or_activity_type': 'ground_transport_rail',
        'factor_value':        0.041,
        'factor_unit':         'kg CO2e / km',
        'source_name':         'DEFRA_2024',
        'source_version':      'DEFRA / DESNZ 2024 Conversion Factors',
        'valid_from_fy':       '2024-25',
        'valid_to_fy':         None,
        'country_code':        'IN',
        'is_active':           True,
        'notes':               'Ground transport — rail/train. Per km.',
    },
]


class Command(BaseCommand):
    help = 'Load official GHG emission factors into the EmissionFactor registry. Safe to re-run.'

    def handle(self, *args, **options):
        created = 0
        updated = 0
        skipped = 0

        for data in FACTORS:
            key = {
                'scope':                data['scope'],
                'fuel_or_activity_type': data['fuel_or_activity_type'],
                'valid_from_fy':        data['valid_from_fy'],
                'country_code':         data['country_code'],
            }
            obj, was_created = EmissionFactor.objects.get_or_create(defaults=data, **key)

            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  [CREATE] {obj.scope} / {obj.fuel_or_activity_type} "
                    f"FY={obj.valid_from_fy} -> {obj.factor_value} {obj.factor_unit}"
                ))
            else:
                # Update if any value has changed
                changed = False
                for field, val in data.items():
                    if field in key:
                        continue
                    if getattr(obj, field) != val:
                        setattr(obj, field, val)
                        changed = True
                if changed:
                    obj.save()
                    updated += 1
                    self.stdout.write(self.style.WARNING(
                        f"  [UPDATE] {obj.scope} / {obj.fuel_or_activity_type} FY={obj.valid_from_fy}"
                    ))
                else:
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDONE: EmissionFactor registry loaded: "
            f"{created} created, {updated} updated, {skipped} unchanged."
        ))
        self.stdout.write(
            f"   Total factors in registry: {EmissionFactor.objects.count()}"
        )
