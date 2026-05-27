"""
Management command: load_navan_fixtures

Loads airport_lookup.json and travel_emission_factors.json into the database.
Safe to run multiple times (uses bulk_create with ignore_conflicts=True).

Usage:
    python manage.py load_navan_fixtures
    python manage.py load_navan_fixtures --fixtures-dir /path/to/dir
"""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = (
        "Load airport_lookup.json and travel_emission_factors.json fixtures "
        "into the database. Safe to re-run — uses ignore_conflicts=True."
    )

    def add_arguments(self, parser):
        default_dir = Path(settings.BASE_DIR) / "fixtures"
        parser.add_argument(
            "--fixtures-dir",
            type=str,
            default=str(default_dir),
            help=f"Directory containing the JSON fixture files (default: {default_dir})",
        )

    def handle(self, *args, **options):
        fixtures_dir = Path(options["fixtures_dir"])
        if not fixtures_dir.exists():
            raise CommandError(f"Fixtures directory not found: {fixtures_dir}")

        self._load_airports(fixtures_dir)
        self._load_emission_factors(fixtures_dir)
        self.stdout.write(self.style.SUCCESS("[OK] Navan fixtures loaded successfully."))

    # ── Loaders ───────────────────────────────────────────────────────────────

    def _load_airports(self, fixtures_dir: Path):
        from apps.emissions.models import AirportLookup

        path = fixtures_dir / "airport_lookup.json"
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"  airport_lookup.json not found in {fixtures_dir}, skipping."))
            return

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        objs = []
        for item in data:
            # Support both "iata_code" (spec) and "iata" (model field)
            iata = item.get("iata") or item.get("iata_code", "")
            if not iata:
                continue
            objs.append(AirportLookup(
                iata    = iata.upper(),
                name    = item.get("name") or item.get("airport_name", ""),
                city    = item.get("city", ""),
                country = item.get("country", ""),
                lat     = item.get("lat") or item.get("latitude", 0),
                lon     = item.get("lon") or item.get("longitude", 0),
            ))

        created = AirportLookup.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"  [OK] AirportLookup: {len(created)} rows inserted (conflicts ignored)."
            )
        )

    def _load_emission_factors(self, fixtures_dir: Path):
        from apps.emissions.models import TravelEmissionFactor

        path = fixtures_dir / "travel_emission_factors.json"
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"  travel_emission_factors.json not found in {fixtures_dir}, skipping."))
            return

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        objs = []
        for item in data:
            objs.append(TravelEmissionFactor(
                category         = item.get("category", ""),
                sub_type         = item.get("sub_type"),
                cabin_class      = item.get("cabin_class"),
                car_category     = item.get("car_category"),
                fuel_type        = item.get("fuel_type"),
                region           = item.get("region"),
                rail_carrier     = item.get("rail_carrier"),
                factor_kg_per_unit = item.get("factor_kg_per_unit", 0),
                unit_description = item.get("unit_description", ""),
                source           = item.get("source", ""),
                vintage_year     = item.get("vintage_year"),
                rfi_included     = item.get("rfi_included", False),
            ))

        created = TravelEmissionFactor.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"  [OK] TravelEmissionFactor: {len(created)} rows inserted (conflicts ignored)."
            )
        )
