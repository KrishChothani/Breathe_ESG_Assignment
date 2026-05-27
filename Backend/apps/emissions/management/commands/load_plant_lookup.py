"""
Management command: load_plant_lookup
Loads fixtures/plant_lookup.json into the lookup_plant table.
Run: python manage.py load_plant_lookup
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.emissions.models import PlantLookup


class Command(BaseCommand):
    help = 'Load plant lookup fixtures from fixtures/plant_lookup.json'

    def handle(self, *args, **options):
        # apps/emissions/management/commands/load_plant_lookup.py → 4 levels up = Backend/
        fixtures_path = Path(__file__).resolve().parents[4] / 'fixtures' / 'plant_lookup.json'

        if not fixtures_path.exists():
            self.stderr.write(self.style.ERROR(f'Fixture not found: {fixtures_path}'))
            return

        with open(fixtures_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        objs = []
        for entry in data:
            objs.append(PlantLookup(
                werks_code    = entry['werks_code'],
                plant_name    = entry['plant_name'],
                city          = entry['city'],
                state         = entry.get('state') or '',
                country       = entry['country'],
                postal_code   = entry.get('postal_code'),
                region        = entry['region'],
                plant_type    = entry.get('plant_type', 'MANUFACTURING'),
                default_scope = entry.get('default_scope', 'SCOPE_1'),
                address_line  = entry.get('address_line'),
                is_active     = entry.get('is_active', True),
                notes         = entry.get('notes'),
            ))

        created = PlantLookup.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(
            f'  [OK] PlantLookup: {len(created)} rows inserted (conflicts ignored).'
        ))
        self.stdout.write(self.style.SUCCESS('[OK] Plant lookup fixtures loaded successfully.'))
