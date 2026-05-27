EMISSION_FACTORS = {
    "DESNZ_2024": {
        "short_haul": {"value": 0.255, "unit": "kg CO2e / km", "year": 2024},
        "medium_haul": {"value": 0.195, "unit": "kg CO2e / km", "year": 2024},
        "long_haul": {"value": 0.150, "unit": "kg CO2e / km", "year": 2024},
    }
}

def classify_flight(distance_km: float, origin_country: str, dest_country: str) -> dict:
    """
    Classifies a flight based on distance and origin/destination countries.
    Returns haul type, domestic/international flag, emission factor metadata, and CO2e.
    """
    if distance_km < 1500:
        haul_type = "short_haul"
    elif distance_km < 4000:
        haul_type = "medium_haul"
    else:
        haul_type = "long_haul"

    is_domestic = bool(origin_country and dest_country and origin_country == dest_country)
    
    # We use DESNZ 2024 for flights
    source = "DESNZ_2024"
    factor_meta = EMISSION_FACTORS[source][haul_type]
    emission_factor_value = factor_meta["value"]
    
    co2e_kg = round(distance_km * emission_factor_value, 2)

    return {
        "haul_type": haul_type,
        "is_domestic": is_domestic,
        "co2e_kg": co2e_kg,
        "emission_factor_value": emission_factor_value,
        "emission_factor_unit": factor_meta["unit"],
        "emission_factor_source": source,
        "emission_factor_year": factor_meta["year"]
    }
