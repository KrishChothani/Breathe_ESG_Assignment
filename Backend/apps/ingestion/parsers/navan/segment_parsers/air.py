"""
AIR segment parser.

Emission calculation uses the Haversine great-circle distance between
departure and arrival airports, multiplied by cabin-class factor and
the DEFRA Radiative Forcing Index (RFI = 1.9).

Reference: DEFRA GHG Conversion Factors 2023, Table 10.
"""

import logging
from decimal import Decimal

from .base import BaseSegmentParser, NormalisedTravelSegment
from ..exceptions import NavanSegmentParseError

logger = logging.getLogger(__name__)

# DEFRA 2023 cabin-class factors (kgCO2e per passenger-km, RFI already applied)
CABIN_FACTORS: dict[str, Decimal] = {
    "ECONOMY":         Decimal("0.133"),
    "PREMIUM_ECONOMY": Decimal("0.206"),
    "BUSINESS":        Decimal("0.429"),
    "FIRST":           Decimal("0.597"),
}

RFI_MULTIPLIER = Decimal("1.9")   # DEFRA standard Radiative Forcing Index


class AirSegmentParser(BaseSegmentParser):
    """
    Parses and computes CO₂e for AIR segments.

    Steps:
    1. Extract all AIR fields; validate required ones.
    2. Guard: same origin == destination → NavanSegmentParseError.
    3. Look up lat/lon for both airports from AirportLookup.
    4. Compute Haversine distance.
    5. Apply cabin-class emission factor × RFI × numberOfPassengers.
    """

    def parse(self, segment: dict) -> NormalisedTravelSegment:
        seg_id = segment.get("segmentId", "<unknown>")
        seg_type = "AIR"

        departure = self._require(segment, "departureAirportCode", seg_id, seg_type).upper()
        arrival = self._require(segment, "arrivalAirportCode", seg_id, seg_type).upper()

        # Guard: same airport is always a data error
        if departure == arrival:
            raise NavanSegmentParseError(
                f"same origin and destination airport: {departure}",
                segment_id=seg_id,
                segment_type=seg_type,
            )

        cabin_raw = (segment.get("cabinClass") or "ECONOMY").upper()
        cabin = cabin_raw if cabin_raw in CABIN_FACTORS else "ECONOMY"
        if cabin != cabin_raw:
            logger.warning("AIR seg %s: unknown cabinClass '%s', defaulting to ECONOMY", seg_id, cabin_raw)

        dep_dt = self._parse_iso_datetime(segment.get("departureDateTime"))
        arr_dt = self._parse_iso_datetime(segment.get("arrivalDateTime"))
        cost_amount, cost_currency = self._parse_cost(segment.get("cost"))

        parsed = NormalisedTravelSegment(
            segment_id=seg_id,
            segment_type=seg_type,
            travel_date=dep_dt.date() if dep_dt else None,
            confirmation_number=segment.get("confirmationNumber", "") or "",
            departure_airport_code=departure,
            arrival_airport_code=arrival,
            airline_carrier=(segment.get("carrier") or segment.get("operatingCarrier") or "").upper(),
            flight_number=segment.get("flightNumber", "") or "",
            cabin_class=cabin,
            fare_class=segment.get("fareClass", "") or "",
            stops=int(segment.get("stops") or 0),
            number_of_passengers=int(segment.get("numberOfPassengers") or 1),
            rfi_applied=True,
            cost_amount=cost_amount,
            cost_currency=cost_currency,
        )
        return parsed

    def compute_co2e(self, parsed: NormalisedTravelSegment) -> NormalisedTravelSegment:
        """
        1. Look up airports in AirportLookup.
        2. Compute Haversine distance.
        3. co2e = distance × cabin_factor × passengers
           (RFI is already baked into DEFRA cabin factors).
        """
        from apps.emissions.models import AirportLookup  # lazy import to avoid circular
        from core.utils.haversine import great_circle_km

        dep_code = parsed.departure_airport_code
        arr_code = parsed.arrival_airport_code

        try:
            dep_airport = AirportLookup.objects.get(iata=dep_code)
            arr_airport = AirportLookup.objects.get(iata=arr_code)
        except AirportLookup.DoesNotExist as exc:
            missing = dep_code if "iata" in str(exc) else arr_code
            parsed.anomaly_flags.append(
                f"airport_lookup_missing: IATA code '{missing}' not found — CO2e uncomputable"
            )
            parsed.status = "FLAGGED"
            return parsed

        distance_km = Decimal(str(great_circle_km(
            float(dep_airport.lat), float(dep_airport.lon),
            float(arr_airport.lat), float(arr_airport.lon),
        ))).quantize(Decimal("0.01"))

        factor = CABIN_FACTORS.get(parsed.cabin_class, CABIN_FACTORS["ECONOMY"])
        passengers = Decimal(str(max(parsed.number_of_passengers, 1)))

        co2e = (distance_km * factor * passengers).quantize(Decimal("0.0001"))

        parsed.distance_km = distance_km
        parsed.co2e_kg = co2e
        parsed.emission_factor_used = factor
        parsed.emission_factor_unit = "kgCO2e per passenger-km (incl. RFI 1.9)"
        parsed.emission_factor_source = "DEFRA 2023"

        return parsed
