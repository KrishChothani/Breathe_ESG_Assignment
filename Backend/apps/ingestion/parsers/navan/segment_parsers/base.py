"""
Abstract base for all Navan segment parsers.

Every concrete parser (air, hotel, car, rail, ground_transport) must
implement parse() and compute_co2e(). Shared helpers (_parse_cost,
_parse_iso_datetime) live here so they are DRY across all subtypes.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ..exceptions import NavanSegmentParseError

logger = logging.getLogger(__name__)


# ── Lightweight parsed-segment data container ─────────────────────────────────

@dataclass
class NormalisedTravelSegment:
    """
    Intermediate, in-memory representation of a single Navan segment
    after parsing but before persistence.

    The normaliser maps this to a TravelRow instance.
    """
    segment_id: str
    segment_type: str                             # AIR | HOTEL | CAR | RAIL | GROUND_TRANSPORT
    travel_date: Optional[datetime] = None
    confirmation_number: str = ""

    # AIR
    departure_airport_code: str = ""
    arrival_airport_code: str = ""
    airline_carrier: str = ""
    flight_number: str = ""
    cabin_class: str = "ECONOMY"
    fare_class: str = ""
    stops: int = 0
    rfi_applied: bool = False
    number_of_passengers: int = 1

    # HOTEL
    hotel_name: str = ""
    hotel_chain_code: str = ""
    check_in_date: Optional[datetime] = None
    check_out_date: Optional[datetime] = None
    number_of_nights: Optional[int] = None
    number_of_rooms: int = 1
    hotel_country: str = ""

    # CAR
    car_vendor: str = ""
    car_category: str = ""
    fuel_type: str = "UNKNOWN"
    car_pickup_datetime: Optional[datetime] = None
    car_dropoff_datetime: Optional[datetime] = None

    # RAIL
    rail_carrier: str = ""
    departure_station: str = ""
    arrival_station: str = ""
    rail_class: str = "STANDARD"

    # GROUND TRANSPORT
    ground_sub_type: str = ""
    ground_provider: str = ""

    # Shared computed
    distance_km: Optional[Decimal] = None
    distance_estimated: bool = False

    # Cost
    cost_amount: Optional[Decimal] = None
    cost_currency: str = ""

    # Emission output (filled by compute_co2e)
    co2e_kg: Optional[Decimal] = None
    emission_factor_used: Optional[Decimal] = None
    emission_factor_unit: str = ""
    emission_factor_source: str = ""

    # Status / flags
    status: str = "PENDING"                       # PENDING | FLAGGED | PARSE_FAILED
    anomaly_flags: list = field(default_factory=list)


# ── Abstract base parser ──────────────────────────────────────────────────────

class BaseSegmentParser(ABC):
    """
    All segment parsers inherit from this.

    Call order enforced by the normaliser::

        parser = AirSegmentParser()
        parsed  = parser.parse(raw_segment_dict)
        parsed  = parser.compute_co2e(parsed)     # mutates & returns
    """

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def parse(self, segment: dict) -> NormalisedTravelSegment:
        """
        Parse the raw segment dict into a NormalisedTravelSegment.
        Must raise NavanSegmentParseError for unrecoverable field errors.
        """

    @abstractmethod
    def compute_co2e(self, parsed: NormalisedTravelSegment) -> NormalisedTravelSegment:
        """
        Compute co2e_kg and fill emission traceability fields.
        Returns the mutated parsed object.
        """

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_cost(cost_dict: dict) -> tuple:
        """
        Safely extract (Decimal amount, str currency) from a cost dict.
        Returns (None, '') if cost_dict is None or malformed.
        """
        if not cost_dict:
            return None, ""
        try:
            amount = Decimal(str(cost_dict.get("amount", 0)))
            currency = str(cost_dict.get("currency", "")).upper()
            return amount, currency
        except Exception:
            return None, ""

    @staticmethod
    def _parse_iso_datetime(dt_str: str) -> Optional[datetime]:
        """
        Parse an ISO 8601 datetime string.  Accepts both UTC 'Z' suffix
        and '+HH:MM' offset forms.  Returns None if the string is empty
        or unparseable — callers must handle None gracefully.
        """
        if not dt_str:
            return None
        # Normalise the trailing Z (Python 3.10 fromisoformat doesn't accept Z)
        cleaned = dt_str.replace("Z", "+00:00")
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M%z",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            logger.warning("_parse_iso_datetime: could not parse '%s'", dt_str)
            return None

    @staticmethod
    def _require(segment: dict, field_name: str, segment_id: str, segment_type: str):
        """Raise NavanSegmentParseError if field_name is missing or empty."""
        val = segment.get(field_name)
        if val is None or (isinstance(val, str) and not val.strip()):
            raise NavanSegmentParseError(
                f"Required field '{field_name}' is missing or empty",
                segment_id=segment_id,
                segment_type=segment_type,
            )
        return val
