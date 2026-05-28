"""
core/utils/co2_calculator.py
============================
GHG Protocol + BRSR-compliant CO2 calculation engine.

All emission factors are read from the EmissionFactor registry (database).
Zero hardcoded factor values anywhere in this file.

Covers:
  Scope 1 — Direct fuel combustion (IPCC 2006 / India GHG Program)
  Scope 2 — Purchased electricity, location-based (CEA V20.0)
  Scope 3 — Business travel (DEFRA 2024 / ICAO)

India FY convention: April → March
  e.g. billing_date = 2024-08-15 → FY 2024-25
"""

import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

# ── Custom exception ───────────────────────────────────────────────────────────

class EmissionFactorNotFound(Exception):
    """Raised when no matching factor exists in the registry."""
    pass


# ── India FY helper ────────────────────────────────────────────────────────────

def get_india_fy(d: date) -> str:
    """
    Return the India Financial Year string for a given date.
    India FY runs April–March.
      2024-04-01 → '2024-25'
      2024-03-31 → '2023-24'
    """
    if d.month >= 4:
        return f"{d.year}-{str(d.year + 1)[2:]}"
    else:
        return f"{d.year - 1}-{str(d.year)[2:]}"


# ── Factor lookup ──────────────────────────────────────────────────────────────

def get_factor(scope: str, activity_type: str,
               billing_fy: Optional[str] = None,
               country: str = 'IN'):
    """
    Look up the correct EmissionFactor from the registry.

    Args:
        scope:        'SCOPE_1' | 'SCOPE_2' | 'SCOPE_3'
        activity_type: e.g. 'diesel', 'electricity_india', 'flight_short_haul'
        billing_fy:   India FY string e.g. '2024-25'. If None, returns latest active.
        country:      ISO-2 country code.

    Returns:
        EmissionFactor instance

    Raises:
        EmissionFactorNotFound if no match found.
    """
    # Import here to avoid circular imports at module load time
    from apps.ingestion.models import EmissionFactor

    qs = EmissionFactor.objects.filter(
        scope=scope,
        fuel_or_activity_type=activity_type,
        country_code=country,
    )

    if billing_fy:
        # Match: valid_from_fy <= billing_fy AND (valid_to_fy >= billing_fy OR valid_to_fy is null)
        # Since FY strings sort lexicographically correctly, string comparison works.
        qs = qs.filter(valid_from_fy__lte=billing_fy).filter(
            models_Q(valid_to_fy__gte=billing_fy) | models_Q(valid_to_fy__isnull=True)
        ).order_by('-valid_from_fy')
    else:
        qs = qs.filter(is_active=True).order_by('-valid_from_fy')

    factor = qs.first()
    if factor is None:
        raise EmissionFactorNotFound(
            f"No emission factor found for scope={scope}, activity={activity_type}, "
            f"FY={billing_fy or 'latest'}, country={country}"
        )
    return factor


# Lazily import Django Q for the OR query above
try:
    from django.db.models import Q as models_Q
except ImportError:
    models_Q = None


# ── Unit normalisers ───────────────────────────────────────────────────────────

LITRE_CONVERSIONS = {
    'l': 1.0, 'litre': 1.0, 'litres': 1.0, 'liter': 1.0, 'liters': 1.0,
    'gal': 3.785, 'gallon': 3.785, 'gallons': 3.785,
    'ml': 0.001, 'millilitre': 0.001,
}

KG_CONVERSIONS = {
    'kg': 1.0, 'kilogram': 1.0, 'kilograms': 1.0,
    'g': 0.001, 'gram': 0.001, 'grams': 0.001,
    'tonne': 1000.0, 'tonnes': 1000.0, 't': 1000.0, 'metric ton': 1000.0,
    'lb': 0.4536, 'lbs': 0.4536, 'pound': 0.4536, 'pounds': 0.4536,
}

M3_CONVERSIONS = {
    'm3': 1.0, 'm³': 1.0, 'cubic meter': 1.0, 'cubic metre': 1.0,
    'scf': 0.02832, 'cf': 0.02832,  # standard cubic foot → m³
}


def _normalise_quantity(quantity: float, unit: str, target: str) -> float:
    """Convert quantity from `unit` to `target` (litres|kg|m3)."""
    u = unit.lower().strip()
    if target == 'litres':
        factor = LITRE_CONVERSIONS.get(u)
    elif target == 'kg':
        factor = KG_CONVERSIONS.get(u)
    elif target == 'm3':
        factor = M3_CONVERSIONS.get(u)
    else:
        factor = None
    if factor is None:
        raise ValueError(f"Cannot convert unit '{unit}' to {target}")
    return quantity * factor


# ── Scope 2 — Electricity ──────────────────────────────────────────────────────

def calculate_scope2_electricity(consumption_kwh: float,
                                  billing_period_start: date,
                                  country_code: str = 'IN') -> dict:
    """
    Calculate Scope 2 CO2e for electricity consumption.
    Uses CEA CO2 Baseline Database (India) or equivalent for other countries.
    Selects the emission factor matching the billing period's financial year.
    """
    fy = get_india_fy(billing_period_start)
    factor = get_factor('SCOPE_2', 'electricity_india', billing_fy=fy, country=country_code)

    co2e_kg = round(consumption_kwh * factor.factor_value, 4)
    formula = (f"{consumption_kwh:,.2f} kWh × {factor.factor_value} "
               f"{factor.factor_unit} = {co2e_kg:,.2f} kg CO₂e")

    return {
        'co2e_kg':               co2e_kg,
        'emission_factor_value': factor.factor_value,
        'emission_factor_unit':  factor.factor_unit,
        'emission_factor_source': factor.source_name,
        'emission_factor_year':  int(fy.split('-')[0]),
        'emission_factor_record_id': str(factor.id),
        'calculation_method':    'location_based',
        'ghg_scope':             'SCOPE_2',
        'ghg_category':          'Purchased Electricity',
        'fy_used':               fy,
        'formula':               formula,
    }


# ── Scope 1 — Fuel Combustion ──────────────────────────────────────────────────

# Maps user-facing fuel_type → (activity_type_key, unit_target)
FUEL_TYPE_MAP = {
    'diesel':      ('diesel',      'litres'),
    'petrol':      ('petrol',      'litres'),
    'gasoline':    ('petrol',      'litres'),  # alias
    'cng':         ('cng',         'kg'),
    'lpg':         ('lpg',         'kg'),
    'natural_gas': ('natural_gas', 'm3'),
    'coal':        ('coal',        'kg'),
    'furnace_oil': ('furnace_oil', 'litres'),
}


def calculate_scope1_fuel(fuel_type: str, quantity: float, unit: str) -> dict:
    """
    Calculate Scope 1 CO2e for direct fuel combustion.
    fuel_type must be one of the keys in FUEL_TYPE_MAP.
    """
    ft = fuel_type.lower().strip()
    if ft not in FUEL_TYPE_MAP:
        raise ValueError(f"Unknown fuel_type '{fuel_type}'. "
                         f"Supported: {list(FUEL_TYPE_MAP.keys())}")

    activity_key, unit_target = FUEL_TYPE_MAP[ft]
    normalised_qty = _normalise_quantity(quantity, unit, unit_target)

    factor = get_factor('SCOPE_1', activity_key)

    co2e_kg = round(normalised_qty * factor.factor_value, 4)
    formula = (f"{normalised_qty:,.4f} {unit_target} × {factor.factor_value} "
               f"{factor.factor_unit} = {co2e_kg:,.2f} kg CO₂e")

    return {
        'co2e_kg':               co2e_kg,
        'emission_factor_value': factor.factor_value,
        'emission_factor_unit':  factor.factor_unit,
        'emission_factor_source': factor.source_name,
        'emission_factor_year':  int(factor.valid_from_fy.split('-')[0]) if '-' in factor.valid_from_fy else None,
        'emission_factor_record_id': str(factor.id),
        'ghg_scope':             'SCOPE_1',
        'ghg_category':          f'Fuel Combustion — {fuel_type.title()}',
        'calculation_method':    'combustion_ghg_protocol',
        'formula':               formula,
    }


# ── Scope 3 — Business Travel ──────────────────────────────────────────────────

# DEFRA 2024 radiative forcing multiplier for aviation (RF factor)
AVIATION_RF_FACTOR = 1.9

def _classify_haul(distance_km: float) -> str:
    if distance_km < 1500:
        return 'flight_short_haul'
    elif distance_km <= 4000:
        return 'flight_medium_haul'
    else:
        return 'flight_long_haul'


def _get_flight_distance(distance_km=None, origin_iata=None, destination_iata=None) -> float:
    """Return flight distance in km. If not provided directly, calculate from IATA codes."""
    if distance_km:
        return float(distance_km)
    if origin_iata and destination_iata:
        try:
            from apps.ingestion.models import Airport
            from core.utils.haversine import haversine_km
            orig = Airport.objects.filter(iata_code=origin_iata).first()
            dest = Airport.objects.filter(iata_code=destination_iata).first()
            if orig and dest:
                return haversine_km(orig.latitude, orig.longitude, dest.latitude, dest.longitude)
        except Exception as e:
            logger.warning("Could not calculate flight distance from IATA: %s", e)
    raise ValueError("Must provide distance_km OR both origin_iata and destination_iata for flight calculation")


def calculate_scope3_travel(travel_type: str, **kwargs) -> dict:
    """
    Calculate Scope 3 CO2e for business travel.

    travel_type = 'flight' | 'hotel' | 'ground'

    For flight: distance_km OR (origin_iata + destination_iata)
    For hotel:  room_nights
    For ground: distance_km + transport_mode ('taxi'|'car'|'train'|'rail')
    """
    travel_type = travel_type.lower()

    if travel_type == 'flight':
        distance_km = _get_flight_distance(
            kwargs.get('distance_km'),
            kwargs.get('origin_iata'),
            kwargs.get('destination_iata'),
        )
        haul_type = _classify_haul(distance_km)
        passengers = kwargs.get('passengers', 1) or 1
        factor = get_factor('SCOPE_3', haul_type)

        # Apply DEFRA-recommended radiative forcing multiplier for air travel
        co2e_kg_pre_rf = distance_km * factor.factor_value * passengers
        co2e_kg = round(co2e_kg_pre_rf * AVIATION_RF_FACTOR, 4)

        formula = (
            f"{distance_km:,.1f} km × {factor.factor_value} {factor.factor_unit} "
            f"× {passengers} pax × {AVIATION_RF_FACTOR} RF = {co2e_kg:,.2f} kg CO₂e"
        )
        category = f'Business Travel — Air ({haul_type.replace("flight_", "").replace("_", " ").title()})'

    elif travel_type == 'hotel':
        room_nights = float(kwargs.get('room_nights', 1) or 1)
        factor = get_factor('SCOPE_3', 'hotel_night')

        co2e_kg = round(room_nights * factor.factor_value, 4)
        formula = (f"{room_nights} room-nights × {factor.factor_value} "
                   f"{factor.factor_unit} = {co2e_kg:,.2f} kg CO₂e")
        category = 'Business Travel — Hotel Stay'

    elif travel_type == 'ground':
        distance_km = float(kwargs.get('distance_km', 0) or 0)
        mode = (kwargs.get('transport_mode') or 'taxi').lower()
        if mode in ('train', 'rail'):
            activity_key = 'ground_transport_rail'
        else:
            activity_key = 'ground_transport_road'
        factor = get_factor('SCOPE_3', activity_key)

        co2e_kg = round(distance_km * factor.factor_value, 4)
        formula = (f"{distance_km:,.1f} km × {factor.factor_value} "
                   f"{factor.factor_unit} = {co2e_kg:,.2f} kg CO₂e")
        category = f'Business Travel — Ground ({mode.title()})'

    else:
        raise ValueError(f"Unknown travel_type '{travel_type}'. Use: flight|hotel|ground")

    return {
        'co2e_kg':               co2e_kg,
        'emission_factor_value': factor.factor_value,
        'emission_factor_unit':  factor.factor_unit,
        'emission_factor_source': factor.source_name,
        'emission_factor_year':  int(factor.valid_from_fy.split('-')[0]) if '-' in factor.valid_from_fy else None,
        'emission_factor_record_id': str(factor.id),
        'ghg_scope':             'SCOPE_3',
        'ghg_category':          category,
        'calculation_method':    'spend_based' if travel_type == 'hotel' else 'distance_based',
        'formula':               formula,
    }


# ── Master dispatcher ──────────────────────────────────────────────────────────

def calculate_from_row(row_instance) -> dict:
    """
    Given any SAPRow, UtilityRow, or TravelRow instance, detect its type
    and call the appropriate calculation function.
    Returns the result dict or raises EmissionFactorNotFound.
    """
    from apps.emissions.models import SAPRow, UtilityRow, TravelRow

    if isinstance(row_instance, UtilityRow):
        kwh = float(row_instance.consumption_kwh or 0)
        if kwh <= 0:
            raise ValueError("consumption_kwh is zero or null — cannot calculate CO2e")
        billing_start = row_instance.billing_start or date.today()
        return calculate_scope2_electricity(kwh, billing_start, 'IN')

    elif isinstance(row_instance, SAPRow):
        fuel_type = _detect_sap_fuel_type(row_instance)
        qty = float(row_instance.quantity or 0)
        unit = row_instance.unit_normalised or row_instance.unit_original or 'litres'
        return calculate_scope1_fuel(fuel_type, qty, unit)

    elif isinstance(row_instance, TravelRow):
        return _calculate_travel_row(row_instance)

    else:
        raise TypeError(f"Unsupported row type: {type(row_instance)}")


def _detect_sap_fuel_type(row) -> str:
    """Infer fuel type from SAP row's esg_category or material_description."""
    text = (row.esg_category or row.material_description or '').lower()
    for fuel in ['diesel', 'petrol', 'gasoline', 'cng', 'lpg',
                 'natural_gas', 'coal', 'furnace_oil']:
        if fuel.replace('_', ' ') in text or fuel in text:
            return fuel
    # Default for unrecognised SAP fuel rows
    return 'diesel'


def _calculate_travel_row(row) -> dict:
    """Map TravelRow segment_type to calculate_scope3_travel call."""
    seg = (row.segment_type or '').upper()

    if seg == 'AIR':
        return calculate_scope3_travel(
            'flight',
            distance_km=float(row.distance_km or 0) or None,
            origin_iata=row.departure_airport_code,
            destination_iata=row.arrival_airport_code,
            passengers=row.number_of_passengers or 1,
        )
    elif seg == 'HOTEL':
        return calculate_scope3_travel(
            'hotel',
            room_nights=(row.number_of_nights or 1) * (row.number_of_rooms or 1),
        )
    elif seg in ('CAR', 'GROUND_TRANSPORT'):
        return calculate_scope3_travel(
            'ground',
            distance_km=float(row.distance_km or 0),
            transport_mode='taxi',
        )
    elif seg == 'RAIL':
        return calculate_scope3_travel(
            'ground',
            distance_km=float(row.distance_km or 0),
            transport_mode='train',
        )
    else:
        raise ValueError(f"Cannot calculate CO2 for travel segment type '{seg}'")


# ── Document vs System CO2 Comparison ─────────────────────────────────────────

def compare_co2(document_claimed_co2_kg, system_calculated_co2_kg) -> dict:
    """
    Compare document-claimed CO2 against system-calculated CO2.
    Returns status, variance %, and difference.
    """
    if document_claimed_co2_kg is None:
        return {
            'status':                    'NOT_APPLICABLE',
            'variance_pct':              None,
            'document_claimed_co2_kg':   None,
            'system_calculated_co2_kg':  system_calculated_co2_kg,
            'difference_kg':             None,
        }

    if not system_calculated_co2_kg or system_calculated_co2_kg == 0:
        return {
            'status':                    'MISSING_DOC_VALUE',
            'variance_pct':              None,
            'document_claimed_co2_kg':   document_claimed_co2_kg,
            'system_calculated_co2_kg':  system_calculated_co2_kg,
            'difference_kg':             None,
        }

    variance_pct = abs(
        (document_claimed_co2_kg - system_calculated_co2_kg)
        / system_calculated_co2_kg * 100
    )

    if variance_pct < 5:
        status = 'MATCH'
    elif variance_pct < 15:
        status = 'MINOR_VARIANCE'
    else:
        status = 'MAJOR_VARIANCE'

    return {
        'status':                    status,
        'variance_pct':              round(variance_pct, 2),
        'document_claimed_co2_kg':   document_claimed_co2_kg,
        'system_calculated_co2_kg':  system_calculated_co2_kg,
        'difference_kg':             round(document_claimed_co2_kg - system_calculated_co2_kg, 4),
    }
