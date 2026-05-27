"""
HOTEL segment parser.

CO₂e is computed as:
    numberOfNights × numberOfRooms × factor_kg_per_room_night

Emission factor is looked up from TravelEmissionFactor by country (ISO 3166-1
alpha-2), falling back to region='GLOBAL' if the country is not in our table.
"""

import logging
from datetime import date
from decimal import Decimal

from .base import BaseSegmentParser, NormalisedTravelSegment
from ..exceptions import NavanSegmentParseError

logger = logging.getLogger(__name__)

GLOBAL_FALLBACK_FACTOR = Decimal("25.0")  # kgCO2e per room-night, IPCC AR6


class HotelSegmentParser(BaseSegmentParser):
    """
    Parses and computes CO₂e for HOTEL segments.

    numberOfNights is computed from checkIn/checkOut when the API sends null,
    which happens frequently for direct-hotel bookings.
    """

    def parse(self, segment: dict) -> NormalisedTravelSegment:
        seg_id = segment.get("segmentId", "<unknown>")
        seg_type = "HOTEL"

        check_in_str = self._require(segment, "checkInDate", seg_id, seg_type)
        check_out_str = self._require(segment, "checkOutDate", seg_id, seg_type)

        check_in = self._parse_iso_datetime(check_in_str)
        check_out = self._parse_iso_datetime(check_out_str)

        # Derive numberOfNights when null
        nights = segment.get("numberOfNights")
        anomaly_flags = []

        if nights is None:
            if check_in and check_out:
                computed = (check_out.date() - check_in.date()).days
                nights = computed
                anomaly_flags.append(
                    f"number_of_nights computed from date diff: {check_in.date()} → {check_out.date()} = {nights} nights"
                )
            else:
                raise NavanSegmentParseError(
                    "numberOfNights is null and checkIn/checkOut cannot be parsed",
                    segment_id=seg_id,
                    segment_type=seg_type,
                )

        nights = int(nights)
        if nights <= 0:
            raise NavanSegmentParseError(
                f"numberOfNights={nights} is not positive (checkIn={check_in_str}, checkOut={check_out_str})",
                segment_id=seg_id,
                segment_type=seg_type,
            )

        address = segment.get("address") or {}
        country = (address.get("country") or "").upper().strip()

        cost_amount, cost_currency = self._parse_cost(segment.get("cost"))

        parsed = NormalisedTravelSegment(
            segment_id=seg_id,
            segment_type=seg_type,
            travel_date=check_in.date() if check_in else None,
            confirmation_number=segment.get("confirmationNumber", "") or "",
            hotel_name=segment.get("hotelName", "") or "",
            hotel_chain_code=segment.get("chainCode", "") or "",
            check_in_date=check_in,
            check_out_date=check_out,
            number_of_nights=nights,
            number_of_rooms=int(segment.get("numberOfRooms") or 1),
            hotel_country=country,
            cost_amount=cost_amount,
            cost_currency=cost_currency,
            anomaly_flags=anomaly_flags,
        )
        return parsed

    def compute_co2e(self, parsed: NormalisedTravelSegment) -> NormalisedTravelSegment:
        """
        Look up emission factor by country, fallback to GLOBAL.
        co2e = nights × rooms × factor_kg_per_room_night
        """
        from apps.emissions.models import TravelEmissionFactor

        country = parsed.hotel_country
        factor_obj = None
        source_region = country or "GLOBAL"

        if country:
            factor_obj = TravelEmissionFactor.objects.filter(
                category="HOTEL", region=country
            ).first()

        if factor_obj is None:
            factor_obj = TravelEmissionFactor.objects.filter(
                category="HOTEL", region="GLOBAL"
            ).first()
            source_region = "GLOBAL"
            if country:
                parsed.anomaly_flags.append(
                    f"hotel_factor_fallback: no factor for country='{country}', using GLOBAL"
                )

        if factor_obj is None:
            # Hard fallback to in-code constant
            factor = GLOBAL_FALLBACK_FACTOR
            source = "IPCC AR6 (in-code fallback)"
            parsed.anomaly_flags.append(
                "hotel_factor_not_in_db: using hard-coded GLOBAL fallback of 25.0 kgCO2e/room-night"
            )
        else:
            factor = Decimal(str(factor_obj.factor_kg_per_unit))
            source = factor_obj.source

        nights = Decimal(str(parsed.number_of_nights))
        rooms = Decimal(str(max(parsed.number_of_rooms, 1)))
        co2e = (nights * rooms * factor).quantize(Decimal("0.0001"))

        parsed.co2e_kg = co2e
        parsed.emission_factor_used = factor
        parsed.emission_factor_unit = f"kgCO2e per room-night [{source_region}]"
        parsed.emission_factor_source = source
        return parsed
