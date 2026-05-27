import math
from decimal import Decimal
from django.test import TestCase
from apps.emissions.models import TravelRow
from apps.ingestion.models import RawUpload, Airport
from apps.organisations.models import Organisation
from apps.ingestion.parsers.travel import TravelAPIParser, haversine_km, _get_coords
from core.utils.emissions import classify_flight

class TestTravelAPIParser(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Test Org")
        self.upload = RawUpload.objects.create(
            organisation=self.org,
            source_type=RawUpload.SourceType.TRAVEL,
            original_filename="test.json"
        )
        self.parser = TravelAPIParser(self.upload)
        
        # Create some Airport records for testing
        Airport.objects.create(
            ident="EGLL", iata_code="LHR", name="London Heathrow",
            latitude=51.4700, longitude=-0.4543,
            airport_type="large_airport", iso_country="GB", iso_region="GB-ENG"
        )
        Airport.objects.create(
            ident="KJFK", iata_code="JFK", name="John F Kennedy International",
            latitude=40.6413, longitude=-73.7781,
            airport_type="large_airport", iso_country="US", iso_region="US-NY"
        )
        Airport.objects.create(
            ident="EGCC", iata_code="MAN", name="Manchester",
            latitude=53.3537, longitude=-2.2749,
            airport_type="large_airport", iso_country="GB", iso_region="GB-ENG"
        )
        
        # Clear the lru_cache for _get_coords between test runs
        _get_coords.cache_clear()

    def tearDown(self):
        _get_coords.cache_clear()

    # --- (a) haversine_km known airports (within 5%)
    def test_haversine_km_lhr_to_jfk(self):
        dist = haversine_km("LHR", "JFK")
        self.assertIsNotNone(dist)
        # Expected ~5540 km
        self.assertTrue(5263 <= dist <= 5817, f"Distance {dist} not within 5% of 5540")

    # --- (b) haversine_km where one IATA is missing
    def test_haversine_km_unknown_iata(self):
        dist = haversine_km("LHR", "UNK")
        self.assertIsNone(dist)

    # --- (c) parse_travel_record with distance provided
    def test_parse_distance_provided(self):
        payload = {
            "segments": [
                {
                    "origin_iata": "LHR",
                    "destination_iata": "JFK",
                    "distance_km": 5500.5
                }
            ]
        }
        rows = self.parser.parse(payload)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.distance_km, Decimal("5500.5"))
        self.assertEqual(row.distance_source, "provided")
        # Ensure it was also classified
        self.assertEqual(row.haul_type, "long_haul")
        self.assertFalse(row.is_domestic)
        self.assertIsNotNone(row.co2e_kg)
        self.assertEqual(row.origin_country, "GB")
        self.assertEqual(row.destination_country, "US")

    # --- (d) parse_travel_record distance calculated
    def test_parse_distance_calculated(self):
        payload = {
            "segments": [
                {
                    "origin_iata": "LHR",
                    "destination_iata": "JFK"
                }
            ]
        }
        rows = self.parser.parse(payload)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.distance_source, "calculated")
        self.assertIsNotNone(row.co2e_kg)
        self.assertEqual(row.haul_type, "long_haul")
        self.assertFalse(row.is_domestic)

    # --- (e) parse_travel_record unknown IATA
    def test_parse_unknown_iata(self):
        payload = {
            "segments": [
                {
                    "origin_iata": "LHR",
                    "destination_iata": "XYZ"
                }
            ]
        }
        rows = self.parser.parse(payload)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.status, TravelRow.Status.PARSE_FAILED)
        self.assertIn("Unknown IATA code: XYZ", row.parse_error)

    # --- (f) & (g) classify_flight tests
    def test_classify_flight_short_domestic(self):
        # distance < 1500, same country
        res = classify_flight(500.0, "GB", "GB")
        self.assertEqual(res["haul_type"], "short_haul")
        self.assertTrue(res["is_domestic"])
        self.assertEqual(res["emission_factor"], 0.255)
        self.assertEqual(res["co2e_kg"], 127.5)  # 500 * 0.255

    def test_classify_flight_medium_intl(self):
        # 1500 <= distance < 4000
        res = classify_flight(2000.0, "GB", "ES")
        self.assertEqual(res["haul_type"], "medium_haul")
        self.assertFalse(res["is_domestic"])
        self.assertEqual(res["emission_factor"], 0.195)
        self.assertEqual(res["co2e_kg"], 390.0)

    def test_classify_flight_long_intl(self):
        # distance >= 4000
        res = classify_flight(5000.0, "GB", "US")
        self.assertEqual(res["haul_type"], "long_haul")
        self.assertFalse(res["is_domestic"])
        self.assertEqual(res["emission_factor"], 0.150)
        self.assertEqual(res["co2e_kg"], 750.0)
