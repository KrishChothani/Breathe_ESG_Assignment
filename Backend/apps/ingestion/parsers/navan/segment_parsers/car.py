"""
CAR segment parser.

CO₂e = estimatedDistanceKm × factor_kg_per_km
Factor looked up by fuelType and carCategory from TravelEmissionFactor.

When estimatedDistanceKm is null, the row is FLAGGED and co2e set to None.
"""

import logging
from decimal import Decimal

from .base import BaseSegmentParser, NormalisedTravelSegment
from ..exceptions import NavanSegmentParseError

logger = logging.getLogger(__name__)

VALID_FUEL_TYPES = {"PETROL", "DIESEL", "HYBRID", "ELECTRIC", "UNKNOWN"}
VALID_CAR_CATEGORIES = {"ECONOMY", "COMPACT", "MIDSIZE", "STANDARD", "FULL_SIZE", "LUXURY", "SUV", "VAN"}


class CarSegmentParser(BaseSegmentParser):
    """Parses CAR rental segments and computes CO₂e based on fuel type and category."""

    def parse(self, segment: dict) -> NormalisedTravelSegment:
        seg_id = segment.get("segmentId", "<unknown>")
        seg_type = "CAR"

        self._require(segment, "pickUpDateTime", seg_id, seg_type)
        self._require(segment, "dropOffDateTime", seg_id, seg_type)

        pickup_dt = self._parse_iso_datetime(segment["pickUpDateTime"])
        dropoff_dt = self._parse_iso_datetime(segment["dropOffDateTime"])

        fuel_raw = (segment.get("fuelType") or "UNKNOWN").upper()
        fuel = fuel_raw if fuel_raw in VALID_FUEL_TYPES else "UNKNOWN"

        cat_raw = (segment.get("carCategory") or "").upper()
        car_cat = cat_raw if cat_raw in VALID_CAR_CATEGORIES else ""

        raw_dist = segment.get("estimatedDistanceKm")
        anomaly_flags = []
        status = "PENDING"

        if raw_dist is None:
            anomaly_flags.append("distance_missing_co2e_uncomputable: estimatedDistanceKm is null")
            status = "FLAGGED"
            distance_km = None
        else:
            distance_km = Decimal(str(raw_dist))

        # Duration for reference
        if pickup_dt and dropoff_dt:
            duration_h = (dropoff_dt - pickup_dt).total_seconds() / 3600
        else:
            duration_h = None

        cost_amount, cost_currency = self._parse_cost(segment.get("cost"))

        pickup_loc = segment.get("pickUpLocation") or {}
        dropoff_loc = segment.get("dropOffLocation") or {}

        parsed = NormalisedTravelSegment(
            segment_id=seg_id,
            segment_type=seg_type,
            travel_date=pickup_dt.date() if pickup_dt else None,
            confirmation_number=segment.get("confirmationNumber", "") or "",
            car_vendor=segment.get("vendor", "") or "",
            car_category=car_cat,
            fuel_type=fuel,
            car_pickup_datetime=pickup_dt,
            car_dropoff_datetime=dropoff_dt,
            distance_km=distance_km,
            cost_amount=cost_amount,
            cost_currency=cost_currency,
            anomaly_flags=anomaly_flags,
            status=status,
        )
        return parsed

    def compute_co2e(self, parsed: NormalisedTravelSegment) -> NormalisedTravelSegment:
        if parsed.distance_km is None:
            # Already flagged in parse()
            parsed.co2e_kg = None
            return parsed

        from apps.emissions.models import TravelEmissionFactor

        # Try exact match on fuel_type + car_category, then just fuel_type
        factor_obj = TravelEmissionFactor.objects.filter(
            category="CAR",
            fuel_type=parsed.fuel_type,
            car_category=parsed.car_category or None,
        ).first()

        if factor_obj is None:
            factor_obj = TravelEmissionFactor.objects.filter(
                category="CAR",
                fuel_type=parsed.fuel_type,
            ).first()

        if factor_obj is None:
            factor_obj = TravelEmissionFactor.objects.filter(
                category="CAR",
                fuel_type="UNKNOWN",
            ).first()
            parsed.anomaly_flags.append(
                f"car_factor_fallback: no factor for fuelType={parsed.fuel_type} "
                f"carCategory={parsed.car_category}, using UNKNOWN fallback"
            )

        if factor_obj is None:
            parsed.anomaly_flags.append("car_factor_not_in_db: CO2e uncomputable")
            parsed.status = "FLAGGED"
            return parsed

        factor = Decimal(str(factor_obj.factor_kg_per_unit))
        co2e = (parsed.distance_km * factor).quantize(Decimal("0.0001"))

        parsed.co2e_kg = co2e
        parsed.emission_factor_used = factor
        parsed.emission_factor_unit = "kgCO2e per km"
        parsed.emission_factor_source = factor_obj.source
        return parsed
