"""
GROUND TRANSPORT segment parser (TAXI | RIDESHARE | LIMO | SHUTTLE | BUS).

When distanceKm is null (common for taxis), distance is estimated from
the cost using a subtype-specific cost-per-km rate:
    TAXI     → 0.50 USD/km
    RIDESHARE → 0.40 USD/km
    LIMO     → 0.80 USD/km
    SHUTTLE  → 0.20 USD/km
    BUS      → 0.10 USD/km

This estimate is noted in anomaly_flags with estimated=True.
"""

import logging
from decimal import Decimal

from .base import BaseSegmentParser, NormalisedTravelSegment
from ..exceptions import NavanSegmentParseError

logger = logging.getLogger(__name__)

VALID_SUBTYPES = {"TAXI", "RIDESHARE", "LIMO", "SHUTTLE", "BUS"}

# Approximate cost-per-km in USD for estimation when distance is null
COST_PER_KM_USD: dict[str, Decimal] = {
    "TAXI":      Decimal("0.50"),
    "RIDESHARE": Decimal("0.40"),
    "LIMO":      Decimal("0.80"),
    "SHUTTLE":   Decimal("0.20"),
    "BUS":       Decimal("0.10"),
}


class GroundTransportParser(BaseSegmentParser):
    """Parses GROUND_TRANSPORT segments and computes CO₂e."""

    def parse(self, segment: dict) -> NormalisedTravelSegment:
        seg_id = segment.get("segmentId", "<unknown>")
        seg_type = "GROUND_TRANSPORT"

        self._require(segment, "pickUpDateTime", seg_id, seg_type)

        sub_raw = (segment.get("subType") or "").upper()
        sub_type = sub_raw if sub_raw in VALID_SUBTYPES else "TAXI"
        if sub_raw not in VALID_SUBTYPES and sub_raw:
            logger.warning(
                "GROUND_TRANSPORT seg %s: unknown subType '%s', defaulting to TAXI",
                seg_id, sub_raw,
            )

        pickup_dt = self._parse_iso_datetime(segment["pickUpDateTime"])
        dropoff_dt = self._parse_iso_datetime(segment.get("dropOffDateTime"))
        cost_amount, cost_currency = self._parse_cost(segment.get("cost"))

        raw_dist = segment.get("distanceKm")
        anomaly_flags = []
        status = "PENDING"
        distance_km = None
        distance_estimated = False

        if raw_dist is not None:
            distance_km = Decimal(str(raw_dist))
        else:
            # Attempt cost-based estimation (in USD equivalent)
            if cost_amount and cost_amount > 0:
                rate = COST_PER_KM_USD.get(sub_type, Decimal("0.50"))
                # Rough estimate — no currency conversion here
                estimated_km = (cost_amount / rate).quantize(Decimal("0.01"))
                distance_km = estimated_km
                distance_estimated = True
                anomaly_flags.append(
                    f"distance_estimated_from_cost: distanceKm null; estimated {estimated_km} km "
                    f"from cost {cost_amount} {cost_currency} at {rate} USD/km [{sub_type}]"
                )
                status = "FLAGGED"
            else:
                anomaly_flags.append(
                    "distance_missing_co2e_uncomputable: distanceKm null and cost unavailable for estimation"
                )
                status = "FLAGGED"

        parsed = NormalisedTravelSegment(
            segment_id=seg_id,
            segment_type=seg_type,
            travel_date=pickup_dt.date() if pickup_dt else None,
            ground_sub_type=sub_type,
            ground_provider=segment.get("provider", "") or "",
            distance_km=distance_km,
            distance_estimated=distance_estimated,
            cost_amount=cost_amount,
            cost_currency=cost_currency,
            anomaly_flags=anomaly_flags,
            status=status,
        )
        return parsed

    def compute_co2e(self, parsed: NormalisedTravelSegment) -> NormalisedTravelSegment:
        if parsed.distance_km is None:
            parsed.co2e_kg = None
            return parsed

        from apps.emissions.models import TravelEmissionFactor

        factor_obj = TravelEmissionFactor.objects.filter(
            category="GROUND_TRANSPORT",
            sub_type=parsed.ground_sub_type,
        ).first()

        if factor_obj is None:
            factor_obj = TravelEmissionFactor.objects.filter(
                category="GROUND_TRANSPORT",
                sub_type="TAXI",
            ).first()
            parsed.anomaly_flags.append(
                f"ground_factor_fallback: no factor for subType={parsed.ground_sub_type}, using TAXI"
            )

        if factor_obj is None:
            parsed.anomaly_flags.append("ground_factor_not_in_db: CO2e uncomputable")
            parsed.status = "FLAGGED"
            return parsed

        factor = Decimal(str(factor_obj.factor_kg_per_unit))
        co2e = (parsed.distance_km * factor).quantize(Decimal("0.0001"))

        parsed.co2e_kg = co2e
        parsed.emission_factor_used = factor
        parsed.emission_factor_unit = "kgCO2e per km"
        parsed.emission_factor_source = factor_obj.source
        return parsed
