"""
Unit tests for the Navan parser module.

Tests are designed to run WITHOUT a real database using Django's TestCase
(which wraps each test in a transaction rollback). DB-dependent parsers
(AirSegmentParser.compute_co2e, HotelSegmentParser.compute_co2e, etc.)
use setUp fixtures to create the required lookup rows.

Run with:
    python manage.py test apps.ingestion.tests.test_navan_parser -v 2
"""

from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock

from django.test import TestCase

from apps.ingestion.parsers.navan.exceptions import NavanSegmentParseError
from apps.ingestion.parsers.navan.segment_parsers.air import AirSegmentParser
from apps.ingestion.parsers.navan.segment_parsers.hotel import HotelSegmentParser
from apps.ingestion.parsers.navan.segment_parsers.car import CarSegmentParser
from apps.ingestion.parsers.navan.segment_parsers.rail import RailSegmentParser
from apps.ingestion.parsers.navan.segment_parsers.ground_transport import GroundTransportParser
from apps.ingestion.serializers import NavanImportTripSerializer


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _make_air_segment(overrides=None):
    base = {
        "type": "AIR",
        "segmentId": "TEST-AIR-001",
        "carrier": "AI",
        "flightNumber": "AI101",
        "departureAirportCode": "BOM",
        "arrivalAirportCode": "LHR",
        "departureDateTime": "2024-03-10T01:45:00+05:30",
        "cabinClass": "BUSINESS",
        "numberOfPassengers": 1,
        "cost": {"amount": "145000.00", "currency": "INR"},
        "stops": 0,
    }
    if overrides:
        base.update(overrides)
    return base


def _make_hotel_segment(overrides=None):
    base = {
        "type": "HOTEL",
        "segmentId": "TEST-HTL-001",
        "hotelName": "The Savoy",
        "checkInDate": "2024-03-10",
        "checkOutDate": "2024-03-13",
        "numberOfNights": 3,
        "numberOfRooms": 1,
        "address": {"country": "GB"},
        "cost": {"amount": "1800.00", "currency": "GBP"},
    }
    if overrides:
        base.update(overrides)
    return base


def _make_car_segment(overrides=None):
    base = {
        "type": "CAR",
        "segmentId": "TEST-CAR-001",
        "vendor": "Hertz",
        "carCategory": "MIDSIZE",
        "fuelType": "PETROL",
        "pickUpDateTime": "2024-03-10T08:00:00+00:00",
        "dropOffDateTime": "2024-03-10T10:00:00+00:00",
        "estimatedDistanceKm": "35.0",
        "cost": {"amount": "85.00", "currency": "GBP"},
    }
    if overrides:
        base.update(overrides)
    return base


# ── AirSegmentParser tests ────────────────────────────────────────────────────

class TestAirSegmentParser(TestCase):

    def setUp(self):
        from apps.emissions.models import AirportLookup
        AirportLookup.objects.create(iata="BOM", name="Mumbai", city="Mumbai", country="IN",
                                     lat=Decimal("19.0896"), lon=Decimal("72.8656"))
        AirportLookup.objects.create(iata="LHR", name="Heathrow", city="London", country="GB",
                                     lat=Decimal("51.4700"), lon=Decimal("-0.4543"))
        from apps.emissions.models import TravelEmissionFactor
        TravelEmissionFactor.objects.create(
            category="AIR", cabin_class="BUSINESS",
            factor_kg_per_unit=Decimal("0.429"),
            unit_description="kgCO2e per passenger-km",
            source="DEFRA 2023", vintage_year=2023, rfi_included=True,
        )
        TravelEmissionFactor.objects.create(
            category="AIR", cabin_class="ECONOMY",
            factor_kg_per_unit=Decimal("0.133"),
            unit_description="kgCO2e per passenger-km",
            source="DEFRA 2023", vintage_year=2023, rfi_included=True,
        )

    def test_valid_business_flight_bom_lhr_co2e_positive(self):
        """BOM→LHR BUSINESS class: co2e should be > 0."""
        parser = AirSegmentParser()
        seg = _make_air_segment()
        parsed = parser.parse(seg)
        parsed = parser.compute_co2e(parsed)

        self.assertIsNotNone(parsed.co2e_kg, "co2e_kg should not be None for a valid flight")
        self.assertGreater(parsed.co2e_kg, Decimal("0"), "co2e_kg must be positive")
        self.assertEqual(parsed.cabin_class, "BUSINESS")
        self.assertEqual(parsed.departure_airport_code, "BOM")
        self.assertEqual(parsed.arrival_airport_code, "LHR")
        # BOM→LHR ≈ 7200 km × 0.429 ≈ 3089 kgCO2e
        self.assertGreater(parsed.co2e_kg, Decimal("2000"))
        self.assertLess(parsed.co2e_kg, Decimal("5000"))

    def test_same_airport_raises_parse_error(self):
        """BOM→BOM must raise NavanSegmentParseError with 'same origin and destination'."""
        parser = AirSegmentParser()
        seg = _make_air_segment({"arrivalAirportCode": "BOM"})
        with self.assertRaises(NavanSegmentParseError) as ctx:
            parser.parse(seg)
        self.assertIn("same origin and destination", str(ctx.exception))

    def test_missing_cabin_class_defaults_to_economy(self):
        """Null cabinClass should default to ECONOMY without raising."""
        parser = AirSegmentParser()
        seg = _make_air_segment({"cabinClass": None})
        parsed = parser.parse(seg)
        self.assertEqual(parsed.cabin_class, "ECONOMY")

    def test_rfi_applied_flag_set(self):
        """rfi_applied must be True for all AIR segments (DEFRA factors include RFI)."""
        parser = AirSegmentParser()
        parsed = parser.parse(_make_air_segment())
        self.assertTrue(parsed.rfi_applied)

    def test_unknown_airport_flags_row(self):
        """An IATA code not in AirportLookup should FLAG the row, not raise."""
        parser = AirSegmentParser()
        seg = _make_air_segment({"departureAirportCode": "ZZZ", "arrivalAirportCode": "LHR"})
        parsed = parser.parse(seg)
        parsed = parser.compute_co2e(parsed)
        self.assertEqual(parsed.status, "FLAGGED")
        self.assertTrue(any("airport_lookup_missing" in f for f in parsed.anomaly_flags))

    def test_multiple_passengers_scales_co2e(self):
        """CO2e should scale linearly with numberOfPassengers."""
        parser = AirSegmentParser()

        parsed1 = parser.parse(_make_air_segment({"numberOfPassengers": 1}))
        parsed1 = parser.compute_co2e(parsed1)

        parsed2 = parser.parse(_make_air_segment({"numberOfPassengers": 2}))
        parsed2 = parser.compute_co2e(parsed2)

        self.assertAlmostEqual(
            float(parsed2.co2e_kg), float(parsed1.co2e_kg) * 2, places=1
        )


# ── HotelSegmentParser tests ──────────────────────────────────────────────────

class TestHotelSegmentParser(TestCase):

    def setUp(self):
        from apps.emissions.models import TravelEmissionFactor
        TravelEmissionFactor.objects.create(
            category="HOTEL", region="GB",
            factor_kg_per_unit=Decimal("20.8"),
            unit_description="kgCO2e per room-night",
            source="BEIS 2023", vintage_year=2023,
        )
        TravelEmissionFactor.objects.create(
            category="HOTEL", region="GLOBAL",
            factor_kg_per_unit=Decimal("25.0"),
            unit_description="kgCO2e per room-night",
            source="IPCC AR6", vintage_year=2023,
        )

    def test_null_nights_computed_from_date_diff(self):
        """numberOfNights=null: should compute 3 nights from 2024-03-10 → 2024-03-13."""
        parser = HotelSegmentParser()
        seg = _make_hotel_segment({"numberOfNights": None})
        parsed = parser.parse(seg)

        self.assertEqual(parsed.number_of_nights, 3)
        self.assertTrue(any("computed from date diff" in f for f in parsed.anomaly_flags))

    def test_null_nights_zero_after_compute_raises(self):
        """numberOfNights computed as 0 (same check-in/out) must raise NavanSegmentParseError."""
        parser = HotelSegmentParser()
        seg = _make_hotel_segment({"checkInDate": "2024-03-10", "checkOutDate": "2024-03-10", "numberOfNights": None})
        with self.assertRaises(NavanSegmentParseError) as ctx:
            parser.parse(seg)
        self.assertIn("not positive", str(ctx.exception))

    def test_co2e_calculated_correctly(self):
        """3 nights × 1 room × 20.8 kgCO2e/room-night = 62.4 kgCO2e for GB."""
        parser = HotelSegmentParser()
        seg = _make_hotel_segment()
        parsed = parser.parse(seg)
        parsed = parser.compute_co2e(parsed)

        self.assertEqual(parsed.co2e_kg, Decimal("62.4000"))

    def test_unknown_country_falls_back_to_global(self):
        """A country not in the factor table should use the GLOBAL fallback."""
        parser = HotelSegmentParser()
        seg = _make_hotel_segment()
        seg["address"]["country"] = "ZZ"  # not in DB
        parsed = parser.parse(seg)
        parsed = parser.compute_co2e(parsed)

        self.assertEqual(parsed.emission_factor_used, Decimal("25.0"))
        self.assertTrue(any("fallback" in f for f in parsed.anomaly_flags))


# ── CarSegmentParser tests ────────────────────────────────────────────────────

class TestCarSegmentParser(TestCase):

    def setUp(self):
        from apps.emissions.models import TravelEmissionFactor
        TravelEmissionFactor.objects.create(
            category="CAR", fuel_type="PETROL", car_category="MIDSIZE",
            factor_kg_per_unit=Decimal("0.192"),
            unit_description="kgCO2e per km",
            source="DEFRA 2023", vintage_year=2023,
        )

    def test_null_distance_sets_flagged_status(self):
        """null estimatedDistanceKm must produce status=FLAGGED and anomaly flag."""
        parser = CarSegmentParser()
        seg = _make_car_segment({"estimatedDistanceKm": None, "cost": {"amount": "0", "currency": "GBP"}})
        parsed = parser.parse(seg)

        self.assertEqual(parsed.status, "FLAGGED")
        self.assertTrue(any("distance_missing" in f for f in parsed.anomaly_flags))

    def test_null_distance_co2e_remains_none(self):
        """null distance → co2e should be None after compute_co2e."""
        parser = CarSegmentParser()
        seg = _make_car_segment({"estimatedDistanceKm": None, "cost": {"amount": "0", "currency": "GBP"}})
        parsed = parser.parse(seg)
        parsed = parser.compute_co2e(parsed)

        self.assertIsNone(parsed.co2e_kg)

    def test_valid_car_co2e(self):
        """35 km × 0.192 = 6.72 kgCO2e for MIDSIZE PETROL."""
        parser = CarSegmentParser()
        seg = _make_car_segment()
        parsed = parser.parse(seg)
        parsed = parser.compute_co2e(parsed)

        self.assertAlmostEqual(float(parsed.co2e_kg), 35.0 * 0.192, places=2)


# ── NavanImportTripSerializer tests ──────────────────────────────────────────

class TestNavanImportTripSerializer(TestCase):

    def _base_payload(self):
        return {
            "externalTripId": "TEST-001",
            "traveler": {"email": "test@example.com"},
            "segments": [
                {
                    "type": "AIR",
                    "segmentId": "SEG-001",
                    "departureAirportCode": "BOM",
                    "arrivalAirportCode": "LHR",
                    "departureDateTime": "2024-01-01T10:00:00Z",
                }
            ],
        }

    def test_valid_payload_passes(self):
        ser = NavanImportTripSerializer(data=self._base_payload())
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_null_segment_type_passes_validation(self):
        """
        Null type must be allowed through (normaliser creates PARSE_FAILED row).
        The serializer must NOT reject a null type.
        """
        payload = self._base_payload()
        payload["segments"] = [{"type": None, "segmentId": "SEG-NULL"}]
        ser = NavanImportTripSerializer(data=payload)
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_unknown_segment_type_raises_validation_error(self):
        """An explicitly unknown string type (not null) must fail validation."""
        payload = self._base_payload()
        payload["segments"] = [{"type": "SPACESHIP", "segmentId": "SEG-BAD"}]
        ser = NavanImportTripSerializer(data=payload)
        self.assertFalse(ser.is_valid())
        self.assertIn("segments", ser.errors)

    def test_missing_traveler_email_raises_error(self):
        payload = self._base_payload()
        payload["traveler"] = {"firstName": "John"}  # no email
        ser = NavanImportTripSerializer(data=payload)
        self.assertFalse(ser.is_valid())
        self.assertIn("traveler", ser.errors)

    def test_empty_segments_list_raises_error(self):
        payload = self._base_payload()
        payload["segments"] = []
        ser = NavanImportTripSerializer(data=payload)
        self.assertFalse(ser.is_valid())
        self.assertIn("segments", ser.errors)


# ── RailSegmentParser tests ───────────────────────────────────────────────────

class TestRailSegmentParser(TestCase):

    def setUp(self):
        from apps.emissions.models import TravelEmissionFactor
        TravelEmissionFactor.objects.create(
            category="RAIL", region="GLOBAL",
            factor_kg_per_unit=Decimal("0.041"),
            unit_description="kgCO2e per passenger-km",
            source="IPCC AR6", vintage_year=2023,
        )

    def test_missing_carrier_raises_error(self):
        """RAIL segment without carrier must raise NavanSegmentParseError."""
        parser = RailSegmentParser()
        seg = {
            "type": "RAIL",
            "segmentId": "TEST-RAIL-001",
            "trainNumber": "ICE504",
            "departureStationCode": "NDLS",
            "arrivalStationCode": "AGC",
            "departureDateTime": "2024-03-17T06:00:00+05:30",
        }
        with self.assertRaises(NavanSegmentParseError) as ctx:
            parser.parse(seg)
        self.assertIn("carrier", str(ctx.exception))

    def test_null_distance_flags_row(self):
        """RAIL without distance should be FLAGGED (distance almost always missing)."""
        parser = RailSegmentParser()
        seg = {
            "type": "RAIL",
            "segmentId": "TEST-RAIL-002",
            "carrier": "Indian Railways",
            "departureStationCode": "NDLS",
            "arrivalStationCode": "AGC",
            "departureDateTime": "2024-03-17T06:00:00+05:30",
            "travelClass": "FIRST",
        }
        parsed = parser.parse(seg)
        parsed = parser.compute_co2e(parsed)

        self.assertEqual(parsed.status, "FLAGGED")
        self.assertIsNone(parsed.co2e_kg)
