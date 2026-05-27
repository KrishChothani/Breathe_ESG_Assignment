"""
core/utils/haversine.py

Haversine great-circle distance calculation.

Used by AirSegmentParser to compute flight distances from IATA airport
coordinates when explicit distance is not available in the API payload.
"""

import math


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance in kilometres between two points
    on Earth specified in decimal degrees (WGS-84).

    Uses the Haversine formula which is accurate to within ~0.3% for
    distances up to 20,000 km — sufficient for flight emission estimates.

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        Great-circle distance in kilometres (float).

    Example:
        >>> great_circle_km(19.0896, 72.8656, 51.4700, -0.4543)  # BOM → LHR
        7188.3...
    """
    R = 6371.0  # Earth's mean radius in km (IUGG 2015)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return R * c
