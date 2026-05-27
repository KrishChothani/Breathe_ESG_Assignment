"""
RAIL segment parser.

CO₂e = distance_km × factor_kg_per_passenger_km × numberOfPassengers

Rail distance is not reliably provided by the Navan API, so this field
is almost always null. When null:
  - The row is set to FLAGGED
  - co2e is set to None
  - An anomaly flag explains why

Emission factors are looked up first by carrier name, then by region.
Deutsche Bahn, Eurostar, etc. publish their own precise factors.
"""

import logging
from decimal import Decimal

from .base import BaseSegmentParser, NormalisedTravelSegment
from ..exceptions import NavanSegmentParseError

logger = logging.getLogger(__name__)


class RailSegmentParser(BaseSegmentParser):
    """Parses RAIL segments and computes CO₂e by carrier or regional factor."""

    def parse(self, segment: dict) -> NormalisedTravelSegment:
        seg_id = segment.get("segmentId", "<unknown>")
        seg_type = "RAIL"

        carrier = self._require(segment, "carrier", seg_id, seg_type)
        self._require(segment, "departureStationCode", seg_id, seg_type)
        self._require(segment, "arrivalStationCode", seg_id, seg_type)
        self._require(segment, "departureDateTime", seg_id, seg_type)

        travel_class_raw = (segment.get("travelClass") or "STANDARD").upper()
        travel_class = travel_class_raw if travel_class_raw in ("STANDARD", "FIRST") else "STANDARD"

        dep_dt = self._parse_iso_datetime(segment["departureDateTime"])
        cost_amount, cost_currency = self._parse_cost(segment.get("cost"))

        parsed = NormalisedTravelSegment(
            segment_id=seg_id,
            segment_type=seg_type,
            travel_date=dep_dt.date() if dep_dt else None,
            confirmation_number=segment.get("confirmationNumber", "") or "",
            rail_carrier=carrier,
            departure_station=segment["departureStationCode"],
            arrival_station=segment["arrivalStationCode"],
            rail_class=travel_class,
            number_of_passengers=int(segment.get("numberOfPassengers") or 1),
            cost_amount=cost_amount,
            cost_currency=cost_currency,
        )
        return parsed

    def compute_co2e(self, parsed: NormalisedTravelSegment) -> NormalisedTravelSegment:
        """
        Rail distance is typically not provided by Navan — flag the row.
        Emission factor is still looked up for reporting; CO2e left null.
        """
        from apps.emissions.models import TravelEmissionFactor

        # Lookup by carrier first
        factor_obj = TravelEmissionFactor.objects.filter(
            category="RAIL",
            rail_carrier__iexact=parsed.rail_carrier,
        ).first()

        if factor_obj is None:
            factor_obj = TravelEmissionFactor.objects.filter(
                category="RAIL",
                region="GLOBAL",
            ).first()
            parsed.anomaly_flags.append(
                f"rail_factor_fallback: no carrier-specific factor for '{parsed.rail_carrier}', using GLOBAL"
            )

        if factor_obj:
            parsed.emission_factor_used = Decimal(str(factor_obj.factor_kg_per_unit))
            parsed.emission_factor_unit = factor_obj.unit_description if hasattr(factor_obj, "unit_description") else "kgCO2e per passenger-km"
            parsed.emission_factor_source = factor_obj.source

        # Distance almost always missing for rail — flag row
        if parsed.distance_km is None:
            parsed.anomaly_flags.append(
                "rail_distance_missing: Navan does not provide rail distance; "
                "CO2e cannot be computed. Manual entry or station-pair lookup required."
            )
            parsed.status = "FLAGGED"
            parsed.co2e_kg = None
        else:
            factor = parsed.emission_factor_used or Decimal("0.041")
            passengers = Decimal(str(max(parsed.number_of_passengers, 1)))
            parsed.co2e_kg = (parsed.distance_km * factor * passengers).quantize(Decimal("0.0001"))

        return parsed
