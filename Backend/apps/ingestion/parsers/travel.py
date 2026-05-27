import math
from functools import lru_cache
from decimal import Decimal
from apps.emissions.models import TravelRow
from apps.ingestion.models import Airport
from core.utils.emissions import classify_flight
from .base import BaseParser

@lru_cache(maxsize=4096)
def _get_coords(iata_code):
    if not iata_code:
        return None
    airport = Airport.objects.filter(iata_code=iata_code.upper()).only("latitude", "longitude").first()
    if airport:
        return (airport.latitude, airport.longitude)
    return None

def get_airport_meta(iata_code):
    if not iata_code:
        return None
    airport = Airport.objects.filter(iata_code=iata_code.upper()).first()
    if airport:
        return {
            "name": airport.name,
            "iso_country": airport.iso_country,
            "iso_region": airport.iso_region,
            "airport_type": airport.airport_type,
            "municipality": airport.municipality,
            "continent": airport.continent
        }
    return None

def haversine_km(origin_iata, destination_iata):
    coords1 = _get_coords(origin_iata)
    coords2 = _get_coords(destination_iata)
    
    if not coords1 or not coords2:
        return None
        
    lat1, lon1 = coords1
    lat2, lon2 = coords2
    
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

class TravelAPIParser(BaseParser):
    def parse(self, payload):
        rows = []
        for item in payload.get('segments', []):
            orig = item.get('origin_iata')
            dest = item.get('destination_iata')
            dist = item.get('distance_km')

            row = TravelRow(
                raw_upload=self.upload,
                organisation=self.upload.organisation,
                segment_type='AIR',
                departure_airport_code=orig,
                arrival_airport_code=dest,
                ghg_scope='SCOPE_3',
                ghg_category='Business travel - air',
            )
            
            orig_meta = get_airport_meta(orig)
            dest_meta = get_airport_meta(dest)
            
            # If IATA code exists in payload but not found in DB
            if (orig and not orig_meta) or (dest and not dest_meta):
                unknown_code = orig if not orig_meta else dest
                row.status = TravelRow.Status.PARSE_FAILED
                row.parse_error = f"Unknown IATA code: {unknown_code} — not found in airport database"
                rows.append(row)
                continue
            
            final_dist = None
            if dist is not None:
                final_dist = float(dist)
                row.distance_km = Decimal(str(dist))
                row.distance_source = "provided"
                row.status = TravelRow.Status.PENDING
            else:
                calculated_dist = haversine_km(orig, dest)
                if calculated_dist is not None:
                    final_dist = calculated_dist
                    row.distance_km = Decimal(str(calculated_dist)).quantize(Decimal("0.01"))
                    row.distance_source = "calculated"
                    row.status = TravelRow.Status.PENDING
                else:
                    row.status = TravelRow.Status.PARSE_FAILED
                    row.parse_error = "Cannot determine distance: no distance_km and no valid IATA codes provided"
            
            # Attach classification and metadata fields
            if final_dist is not None and orig_meta and dest_meta:
                orig_country = orig_meta.get("iso_country")
                dest_country = dest_meta.get("iso_country")
                
                classification = classify_flight(final_dist, orig_country, dest_country)
                
                row.haul_type = classification["haul_type"]
                row.is_domestic = classification["is_domestic"]
                row.co2e_kg = Decimal(str(classification["co2e_kg"]))
                row.origin_country = orig_country
                row.destination_country = dest_country
                
            rows.append(row)
        return rows

    def validate(self):
        pass

    def normalise(self):
        pass
