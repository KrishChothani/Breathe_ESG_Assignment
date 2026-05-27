"""
NavanTripNormaliser — orchestrates the full parse → compute → persist pipeline.

Given a raw importTrip payload dict and a RawUpload UUID, it:
1. Reads traveler metadata from the trip.
2. Dispatches each segment to the correct segment parser by type.
3. Calls compute_co2e() on the parsed result.
4. Converts NormalisedTravelSegment → TravelRow (unsaved).
5. Catches NavanSegmentParseError per-segment so one bad segment never
   aborts the whole trip.

The caller (view) saves all rows via TravelRow.objects.bulk_create(rows).
"""

import logging
import uuid
from typing import List

from .exceptions import NavanSegmentParseError
from .segment_parsers.air import AirSegmentParser
from .segment_parsers.hotel import HotelSegmentParser
from .segment_parsers.car import CarSegmentParser
from .segment_parsers.rail import RailSegmentParser
from .segment_parsers.ground_transport import GroundTransportParser

logger = logging.getLogger(__name__)

# Map segment type string → parser class
_PARSERS = {
    "AIR":              AirSegmentParser,
    "HOTEL":            HotelSegmentParser,
    "CAR":              CarSegmentParser,
    "RAIL":             RailSegmentParser,
    "GROUND_TRANSPORT": GroundTransportParser,
}


class NavanTripNormaliser:
    """
    Converts a raw Navan importTrip payload into a list of unsaved TravelRow
    model instances, one per segment.

    Usage::

        normaliser = NavanTripNormaliser()
        rows = normaliser.normalise(raw_trip_dict, raw_upload_id)
        TravelRow.objects.bulk_create(rows)
    """

    def normalise(self, raw_trip: dict, raw_upload_id: uuid.UUID) -> List:
        """
        Main entry point. Returns a list of (unsaved) TravelRow instances.

        Segments that fail parsing produce a PARSE_FAILED TravelRow so the
        overall import still succeeds and the analyst can review the failure.
        """
        from apps.emissions.models import TravelRow
        from apps.ingestion.models import RawUpload

        # ── Trip-level metadata ───────────────────────────────────────────────
        traveler = raw_trip.get("traveler") or {}
        traveler_email = traveler.get("email", "")
        traveler_employee_id = traveler.get("employeeId", "") or ""
        navan_trip_id = raw_trip.get("tripId", "")         # populated after Navan import
        external_trip_id = raw_trip.get("externalTripId", "") or ""
        trip_name = raw_trip.get("tripName", "") or ""
        booking_source = raw_trip.get("bookingSource", "") or ""

        try:
            raw_upload = RawUpload.objects.get(id=raw_upload_id)
        except RawUpload.DoesNotExist:
            logger.error("RawUpload %s not found — cannot attach TravelRows", raw_upload_id)
            return []

        rows: List[TravelRow] = []
        segments = raw_trip.get("segments") or []

        for idx, segment in enumerate(segments):
            seg_type = segment.get("type") if isinstance(segment, dict) else None
            seg_id = (segment.get("segmentId") if isinstance(segment, dict) else None) or f"seg-{idx}"

            # ── Guard: null / unknown type ────────────────────────────────────
            if not seg_type or seg_type not in _PARSERS:
                reason = (
                    f"PARSE_FAILED: null segment type" if not seg_type
                    else f"PARSE_FAILED: unknown segment type '{seg_type}'"
                )
                row = TravelRow(
                    raw_upload=raw_upload,
                    traveller_email=traveler_email,
                    traveler_employee_id=traveler_employee_id,
                    navan_trip_id=navan_trip_id,
                    external_trip_id=external_trip_id,
                    trip_name=trip_name,
                    booking_source=booking_source,
                    segment_id=seg_id,
                    segment_type="UNKNOWN",
                    status="PARSE_FAILED",
                    anomaly_flags=[reason],
                )
                rows.append(row)
                logger.warning("Segment %s: %s", seg_id, reason)
                continue

            # ── Parse & compute CO2e ──────────────────────────────────────────
            parser_cls = _PARSERS[seg_type]
            parser = parser_cls()

            try:
                parsed = parser.parse(segment)
                parsed = parser.compute_co2e(parsed)
            except NavanSegmentParseError as exc:
                logger.warning("Segment %s parse error: %s", seg_id, exc)
                row = TravelRow(
                    raw_upload=raw_upload,
                    traveller_email=traveler_email,
                    traveler_employee_id=traveler_employee_id,
                    navan_trip_id=navan_trip_id,
                    external_trip_id=external_trip_id,
                    trip_name=trip_name,
                    booking_source=booking_source,
                    segment_id=seg_id,
                    segment_type=seg_type,
                    status="PARSE_FAILED",
                    anomaly_flags=[exc.to_flag()],
                )
                rows.append(row)
                continue
            except Exception as exc:
                logger.exception("Unexpected error parsing segment %s: %s", seg_id, exc)
                row = TravelRow(
                    raw_upload=raw_upload,
                    traveller_email=traveler_email,
                    traveler_employee_id=traveler_employee_id,
                    navan_trip_id=navan_trip_id,
                    external_trip_id=external_trip_id,
                    trip_name=trip_name,
                    booking_source=booking_source,
                    segment_id=seg_id,
                    segment_type=seg_type,
                    status="PARSE_FAILED",
                    anomaly_flags=[f"UNEXPECTED_ERROR: {exc}"],
                )
                rows.append(row)
                continue

            # ── Map NormalisedTravelSegment → TravelRow ───────────────────────
            row = self._to_travel_row(
                parsed=parsed,
                raw_upload=raw_upload,
                traveler_email=traveler_email,
                traveler_employee_id=traveler_employee_id,
                navan_trip_id=navan_trip_id,
                external_trip_id=external_trip_id,
                trip_name=trip_name,
                booking_source=booking_source,
            )
            rows.append(row)

        logger.info(
            "NavanTripNormaliser: trip=%s segments=%d rows_produced=%d",
            external_trip_id, len(segments), len(rows),
        )
        return rows

    # ── Private mapper ────────────────────────────────────────────────────────

    @staticmethod
    def _to_travel_row(
        parsed,
        raw_upload,
        traveler_email: str,
        traveler_employee_id: str,
        navan_trip_id: str,
        external_trip_id: str,
        trip_name: str,
        booking_source: str,
    ):
        from apps.emissions.models import TravelRow

        # Determine final status
        status = parsed.status or "PENDING"
        if parsed.anomaly_flags and status == "PENDING":
            status = "FLAGGED"

        cat_map = {
            "AIR": "Business travel - air",
            "HOTEL": "Business travel - hotel",
            "CAR": "Business travel - car",
            "RAIL": "Business travel - rail",
            "GROUND_TRANSPORT": "Business travel - ground",
        }
        ghg_category = cat_map.get(parsed.segment_type, "Business travel")

        return TravelRow(
            # Core NormalisedRow fields
            raw_upload=raw_upload,
            status=status,
            co2e_kg=parsed.co2e_kg,
            anomaly_flags=parsed.anomaly_flags or [],

            # Trip-level
            traveller_email=traveler_email,
            traveler_employee_id=traveler_employee_id,
            navan_trip_id=navan_trip_id,
            external_trip_id=external_trip_id,
            trip_name=trip_name,
            booking_source=booking_source,

            # Segment common
            segment_id=parsed.segment_id,
            segment_type=parsed.segment_type,
            travel_date=parsed.travel_date,
            confirmation_number=parsed.confirmation_number,

            # AIR
            departure_airport_code=parsed.departure_airport_code,
            arrival_airport_code=parsed.arrival_airport_code,
            airline_carrier=parsed.airline_carrier,
            flight_number=parsed.flight_number,
            cabin_class=parsed.cabin_class,
            fare_class=parsed.fare_class,
            stops=parsed.stops,
            rfi_applied=parsed.rfi_applied,
            number_of_passengers=parsed.number_of_passengers,

            # HOTEL
            hotel_name=parsed.hotel_name,
            hotel_chain_code=parsed.hotel_chain_code,
            check_in_date=parsed.check_in_date,
            check_out_date=parsed.check_out_date,
            number_of_nights=parsed.number_of_nights,
            number_of_rooms=parsed.number_of_rooms,
            hotel_country=parsed.hotel_country,

            # CAR
            car_vendor=parsed.car_vendor,
            car_category=parsed.car_category,
            fuel_type=parsed.fuel_type,
            car_pickup_datetime=parsed.car_pickup_datetime,
            car_dropoff_datetime=parsed.car_dropoff_datetime,

            # RAIL
            rail_carrier=parsed.rail_carrier,
            departure_station=parsed.departure_station,
            arrival_station=parsed.arrival_station,
            rail_class=parsed.rail_class,

            # GROUND
            ground_sub_type=parsed.ground_sub_type,
            ground_provider=parsed.ground_provider,

            # Shared computed
            distance_km=parsed.distance_km,
            distance_estimated=parsed.distance_estimated,

            # Cost
            cost_amount=parsed.cost_amount,
            cost_currency=parsed.cost_currency,

            # Emission traceability
            ghg_scope='SCOPE_3',
            ghg_category=ghg_category,
            emission_factor_value=getattr(parsed, 'emission_factor_value', getattr(parsed, 'emission_factor_used', None)),
            emission_factor_unit=parsed.emission_factor_unit,
            emission_factor_source=parsed.emission_factor_source,
            emission_factor_year=getattr(parsed, 'emission_factor_year', None),
        )
