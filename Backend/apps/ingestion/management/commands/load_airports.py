import csv
from django.core.management.base import BaseCommand
from apps.ingestion.models import Airport

class Command(BaseCommand):
    help = 'Load global airports from the OurAirports CSV dataset'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the OurAirports CSV file')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                airports_to_create = []
                skipped = 0
                loaded = 0
                
                for row in reader:
                    iata = row.get('iata_code', '').strip()
                    if not iata or iata == '0':
                        skipped += 1
                        continue
                        
                    airport_type = row.get('type', '').strip()
                    if airport_type in ('closed', 'balloonport'):
                        skipped += 1
                        continue
                        
                    try:
                        lat = float(row.get('latitude_deg'))
                        lon = float(row.get('longitude_deg'))
                    except (ValueError, TypeError):
                        skipped += 1
                        continue
                        
                    airport = Airport(
                        ident=row.get('ident', '').strip(),
                        iata_code=iata,
                        name=row.get('name', '').strip()[:255],
                        latitude=lat,
                        longitude=lon,
                        airport_type=airport_type[:50],
                        iso_country=row.get('iso_country', '').strip()[:2],
                        iso_region=row.get('iso_region', '').strip()[:10],
                        municipality=row.get('municipality', '').strip()[:255] if row.get('municipality') else None,
                        continent=row.get('continent', '').strip()[:2] if row.get('continent') else None,
                    )
                    airports_to_create.append(airport)
                    loaded += 1
                    
                if airports_to_create:
                    # chunking might be needed if there are 70k, but bulk_create can handle it, 
                    # though SQLite has limits on query variables. We'll batch it just in case.
                    batch_size = 999
                    for i in range(0, len(airports_to_create), batch_size):
                        Airport.objects.bulk_create(
                            airports_to_create[i:i+batch_size],
                            update_conflicts=True,
                            update_fields=['latitude', 'longitude', 'name', 'airport_type', 'municipality'],
                            unique_fields=['ident']
                        )
                    
                self.stdout.write(self.style.SUCCESS(f"Done. Loaded {loaded} airports, skipped {skipped} rows"))
                
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Error: File not found at path: {csv_path}"))
        except UnicodeDecodeError:
            self.stderr.write(self.style.ERROR(f"Error: Could not decode file at path: {csv_path}. Please ensure it is UTF-8 encoded."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
