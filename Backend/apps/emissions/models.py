"""
apps/emissions/models.py — Multi-tenant edition
================================================
All data models are now scoped to an Organisation.

NormalisedRow (abstract) inherits TenantModel so SAPRow, UtilityRow,
TravelRow automatically get organisation FK + timestamps.

Reference/lookup tables (PlantLookup, GridEmissionFactor, AirportLookup,
TravelEmissionFactor) also get organisation FK so each company can maintain
their own lookup sets independently.
"""

import uuid
from django.db import models
from django.conf import settings
from apps.ingestion.models import RawUpload
from core.models import TenantModel


# ── Abstract base ─────────────────────────────────────────────────────────────

class NormalisedRow(TenantModel):
    """
    Abstract base for every normalised data row regardless of source.
    Inherits organisation FK + timestamps from TenantModel.
    """

    class Status(models.TextChoices):
        PENDING      = 'PENDING',      'Pending review'
        FLAGGED      = 'FLAGGED',      'Flagged for attention'
        APPROVED     = 'APPROVED',     'Approved by analyst'
        REJECTED     = 'REJECTED',     'Rejected'
        LOCKED       = 'LOCKED',       'Locked — sent to auditor'
        PARSE_FAILED = 'PARSE_FAILED', 'Parse failed'

    class Scope(models.TextChoices):
        SCOPE_1 = 'SCOPE_1', 'Scope 1'
        SCOPE_2 = 'SCOPE_2', 'Scope 2'
        SCOPE_3 = 'SCOPE_3', 'Scope 3'

    class EmissionFactorSource(models.TextChoices):
        DEFRA_2024 = 'DEFRA_2024', 'DEFRA 2024'
        DESNZ_2024 = 'DESNZ_2024', 'DESNZ 2024'
        IPCC_AR6   = 'IPCC_AR6',   'IPCC AR6'
        ICAO_2023  = 'ICAO_2023',  'ICAO 2023'
        CUSTOM     = 'CUSTOM',     'Custom'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    raw_upload = models.ForeignKey(
        RawUpload, on_delete=models.CASCADE, related_name='%(class)s_rows'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    anomaly_flags = models.JSONField(default=list, blank=True)
    parse_error   = models.TextField(blank=True)
    co2e_kg       = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

    ghg_scope     = models.CharField(max_length=20, choices=Scope.choices, null=True, blank=True)
    ghg_category  = models.CharField(max_length=100, null=True, blank=True)
    
    emission_factor_value  = models.FloatField(null=True, blank=True)
    emission_factor_unit   = models.CharField(max_length=100, null=True, blank=True)
    emission_factor_source = models.CharField(max_length=50, choices=EmissionFactorSource.choices, null=True, blank=True)
    emission_factor_year   = models.IntegerField(null=True, blank=True)
    # Registry FK — records exactly which EmissionFactor record was used (for audit trail)
    emission_factor_record_id = models.UUIDField(null=True, blank=True,
        help_text='UUID of the EmissionFactor registry record used for this calculation')
    # Human-readable formula string: e.g. '4280 kWh x 0.710 kg CO2e/kWh = 3038.8 kg'
    formula = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True


# ── Scope 1 / 2 row types ─────────────────────────────────────────────────────

class SAPRow(NormalisedRow):
    """
    Normalised row from an SAP ME2M / MB51 flat-file export.
    Handles German header variants, WERKS plant lookup, and MEINS unit mapping.
    """
    po_number            = models.CharField(max_length=20, blank=True)
    line_item            = models.CharField(max_length=10, blank=True)
    material_code        = models.CharField(max_length=40, blank=True)
    material_description = models.CharField(max_length=255, blank=True)
    plant_code           = models.CharField(max_length=20, blank=True)
    plant_name           = models.CharField(max_length=255, blank=True)
    vendor_id            = models.CharField(max_length=20, blank=True)
    quantity             = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    unit_original        = models.CharField(max_length=20, blank=True)
    unit_normalised      = models.CharField(max_length=20, blank=True)
    net_value            = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency             = models.CharField(max_length=5, blank=True)
    document_date        = models.DateField(null=True, blank=True)
    esg_category         = models.CharField(max_length=100, blank=True)
    # Document vs System CO2 comparison (SAP docs sometimes state CO2 claims)
    document_claimed_co2_kg  = models.FloatField(null=True, blank=True)
    system_calculated_co2_kg = models.FloatField(null=True, blank=True)
    co2_variance_pct         = models.FloatField(null=True, blank=True)
    co2_comparison_status    = models.CharField(max_length=30, null=True, blank=True, choices=[
        ('NOT_APPLICABLE',    'Not Applicable'),
        ('MATCH',             'Match — variance < 5%'),
        ('MINOR_VARIANCE',    'Minor Variance — 5% to 15%'),
        ('MAJOR_VARIANCE',    'Major Variance — > 15%'),
        ('MISSING_DOC_VALUE', 'Missing Document Value'),
    ])

    class Meta:
        verbose_name        = 'SAP Row'
        verbose_name_plural = 'SAP Rows'
        indexes = [
            models.Index(fields=['plant_code']),
            models.Index(fields=['document_date']),
            models.Index(fields=['esg_category']),
            models.Index(fields=['organisation']),
        ]

    def __str__(self):
        return f"SAP PO {self.po_number}/{self.line_item} — {self.plant_code}"


class UtilityRow(NormalisedRow):
    """
    Normalised row from a utility portal CSV.
    """
    account_number       = models.CharField(max_length=100, blank=True)
    meter_id             = models.CharField(max_length=100, blank=True)
    site_name            = models.CharField(max_length=255, blank=True)
    billing_start        = models.DateField(null=True, blank=True)
    billing_end          = models.DateField(null=True, blank=True)
    period_month         = models.CharField(max_length=7, blank=True, db_index=True)
    consumption_original = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    unit_original        = models.CharField(max_length=20, blank=True)
    consumption_kwh      = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    grid_factor_used     = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    grid_factor_vintage_year = models.SmallIntegerField(null=True, blank=True)
    # Document vs System CO2 comparison
    document_claimed_co2_kg  = models.FloatField(null=True, blank=True,
        help_text='CO2 figure extracted directly from the utility bill document')
    system_calculated_co2_kg = models.FloatField(null=True, blank=True,
        help_text='CO2 computed by the BreatheESG calculation engine')
    co2_variance_pct         = models.FloatField(null=True, blank=True,
        help_text='abs((doc - system) / system) x 100')
    co2_comparison_status    = models.CharField(max_length=30, null=True, blank=True, choices=[
        ('NOT_APPLICABLE',    'Not Applicable — no document CO2 claim'),
        ('MATCH',             'Match — variance < 5%'),
        ('MINOR_VARIANCE',    'Minor Variance — 5% to 15%'),
        ('MAJOR_VARIANCE',    'Major Variance — > 15%'),
        ('MISSING_DOC_VALUE', 'Missing Document Value'),
    ])

    class Meta:
        verbose_name        = 'Utility Row'
        verbose_name_plural = 'Utility Rows'
        indexes = [
            models.Index(fields=['meter_id']),
            models.Index(fields=['period_month']),
            models.Index(fields=['organisation']),
        ]

    def __str__(self):
        return f"Utility {self.meter_id} — {self.period_month}"


# ── Scope 3 — Travel ──────────────────────────────────────────────────────────

class TravelRow(NormalisedRow):
    """
    Normalised row from the Navan or Concur travel API.
    """

    class SegmentType(models.TextChoices):
        AIR              = 'AIR',              'Air'
        HOTEL            = 'HOTEL',            'Hotel'
        CAR              = 'CAR',              'Car Rental'
        RAIL             = 'RAIL',             'Rail'
        GROUND_TRANSPORT = 'GROUND_TRANSPORT', 'Ground Transport'
        UNKNOWN          = 'UNKNOWN',          'Unknown / Parse Failed'

    class CabinClass(models.TextChoices):
        ECONOMY         = 'ECONOMY',         'Economy'
        PREMIUM_ECONOMY = 'PREMIUM_ECONOMY', 'Premium Economy'
        BUSINESS        = 'BUSINESS',        'Business'
        FIRST           = 'FIRST',           'First'

    # ── Trip-level ────────────────────────────────────────────────────────────
    navan_trip_id        = models.CharField(max_length=100, null=True, blank=True)
    external_trip_id     = models.CharField(max_length=100, null=True, blank=True)
    trip_name            = models.CharField(max_length=255, null=True, blank=True)
    traveller_email      = models.EmailField(blank=True)
    traveler_employee_id = models.CharField(max_length=100, null=True, blank=True)
    booking_source       = models.CharField(max_length=100, null=True, blank=True)

    # ── Segment common ────────────────────────────────────────────────────────
    segment_id      = models.CharField(max_length=100, blank=True)
    segment_type    = models.CharField(
        max_length=20, choices=SegmentType.choices, default=SegmentType.UNKNOWN, db_index=True
    )
    travel_date         = models.DateField(null=True, blank=True)
    confirmation_number = models.CharField(max_length=100, null=True, blank=True)

    # ── AIR ───────────────────────────────────────────────────────────────────
    departure_airport_code = models.CharField(max_length=10, null=True, blank=True)
    arrival_airport_code   = models.CharField(max_length=10, null=True, blank=True)
    airline_carrier        = models.CharField(max_length=10, null=True, blank=True)
    flight_number          = models.CharField(max_length=20, null=True, blank=True)
    cabin_class            = models.CharField(max_length=20, choices=CabinClass.choices, null=True, blank=True)
    fare_class             = models.CharField(max_length=5, null=True, blank=True)
    stops                  = models.IntegerField(null=True, blank=True)
    rfi_applied            = models.BooleanField(default=False)

    # ── HOTEL ─────────────────────────────────────────────────────────────────
    hotel_name       = models.CharField(max_length=255, null=True, blank=True)
    hotel_chain_code = models.CharField(max_length=10, null=True, blank=True)
    check_in_date    = models.DateField(null=True, blank=True)
    check_out_date   = models.DateField(null=True, blank=True)
    number_of_nights = models.IntegerField(null=True, blank=True)
    number_of_rooms  = models.IntegerField(null=True, default=1)
    hotel_country    = models.CharField(max_length=5, null=True, blank=True)

    # ── CAR ───────────────────────────────────────────────────────────────────
    car_vendor           = models.CharField(max_length=100, null=True, blank=True)
    car_category         = models.CharField(max_length=30, null=True, blank=True)
    fuel_type            = models.CharField(max_length=20, null=True, blank=True)
    car_pickup_datetime  = models.DateTimeField(null=True, blank=True)
    car_dropoff_datetime = models.DateTimeField(null=True, blank=True)

    # ── RAIL ──────────────────────────────────────────────────────────────────
    rail_carrier      = models.CharField(max_length=100, null=True, blank=True)
    departure_station = models.CharField(max_length=100, null=True, blank=True)
    arrival_station   = models.CharField(max_length=100, null=True, blank=True)
    rail_class        = models.CharField(max_length=20, null=True, blank=True)

    # ── GROUND TRANSPORT ──────────────────────────────────────────────────────
    ground_sub_type = models.CharField(max_length=30, null=True, blank=True)
    ground_provider = models.CharField(max_length=100, null=True, blank=True)

    # ── Shared computed ───────────────────────────────────────────────────────
    distance_km          = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    distance_source      = models.CharField(max_length=20, blank=True)
    distance_estimated   = models.BooleanField(default=False)
    number_of_passengers = models.IntegerField(default=1)

    # ── Cost ──────────────────────────────────────────────────────────────────
    cost_amount   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_currency = models.CharField(max_length=5, null=True, blank=True)

    class Meta:
        db_table            = 'emissions_travel_row'
        verbose_name        = 'Travel Row'
        verbose_name_plural = 'Travel Rows'
        indexes = [
            models.Index(fields=['segment_type']),
            models.Index(fields=['travel_date']),
            models.Index(fields=['traveller_email']),
            models.Index(fields=['external_trip_id']),
            models.Index(fields=['organisation']),
        ]

    def __str__(self):
        return (
            f"Travel [{self.segment_type}] "
            f"{self.departure_airport_code or self.departure_station or ''}"
            f" -> "
            f"{self.arrival_airport_code or self.arrival_station or self.hotel_name or ''}"
        )


# ── Reference / Lookup Tables (now also tenant-scoped) ────────────────────────

class PlantLookup(models.Model):
    """
    Maps SAP WERKS plant codes to real location and emissions metadata.
    Now scoped to Organisation — werks_code unique per org, not globally.
    """

    class Region(models.TextChoices):
        ASIA_PACIFIC  = 'ASIA_PACIFIC',  'Asia Pacific'
        EUROPE        = 'EUROPE',        'Europe'
        NORTH_AMERICA = 'NORTH_AMERICA', 'North America'
        MIDDLE_EAST   = 'MIDDLE_EAST',   'Middle East'
        AFRICA        = 'AFRICA',        'Africa'
        LATIN_AMERICA = 'LATIN_AMERICA', 'Latin America'

    class PlantType(models.TextChoices):
        MANUFACTURING = 'MANUFACTURING', 'Manufacturing Factory'
        WAREHOUSE     = 'WAREHOUSE',     'Warehouse / Distribution Centre'
        OFFICE        = 'OFFICE',        'Office / HQ'
        RETAIL        = 'RETAIL',        'Retail Outlet'
        CONSTRUCTION  = 'CONSTRUCTION',  'Construction Site'
        DATA_CENTRE   = 'DATA_CENTRE',   'Data Centre'
        OTHER         = 'OTHER',         'Other'

    class Scope(models.TextChoices):
        SCOPE_1   = 'SCOPE_1',   'Scope 1 - Direct emissions'
        SCOPE_2   = 'SCOPE_2',   'Scope 2 - Indirect from purchased electricity'
        SCOPE_1_2 = 'SCOPE_1_2', 'Both Scope 1 and Scope 2'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Tenant scope ──────────────────────────────────────────────────────────
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='plant_lookups',
        db_index=True,
    )

    # ── SAP identifier (unique per organisation, not globally) ────────────────
    werks_code = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Exact SAP WERKS code e.g. 1000, IN_MUM, DE01"
    )

    plant_name   = models.CharField(max_length=255)
    address_line = models.CharField(max_length=255, blank=True, null=True)
    city         = models.CharField(max_length=100)
    state        = models.CharField(max_length=100, blank=True, null=True)
    country      = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    postal_code  = models.CharField(max_length=20, blank=True, null=True)

    region        = models.CharField(max_length=30, choices=Region.choices)
    plant_type    = models.CharField(max_length=30, choices=PlantType.choices, default=PlantType.MANUFACTURING)
    default_scope = models.CharField(max_length=10, choices=Scope.choices, default=Scope.SCOPE_1)

    grid_emission_factor = models.ForeignKey(
        'GridEmissionFactor', null=True, blank=True, on_delete=models.SET_NULL,
    )

    is_active  = models.BooleanField(default=True)
    added_by   = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='plant_lookups_added'
    )
    notes      = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = 'lookup_plant'
        ordering        = ['country', 'city', 'werks_code']
        # werks_code unique per organisation (not globally)
        unique_together = [('organisation', 'werks_code')]
        verbose_name        = 'Plant Lookup'
        verbose_name_plural = 'Plant Lookups'

    def __str__(self):
        return f"{self.werks_code} - {self.plant_name} ({self.city}, {self.country})"


class MaterialGroupMap(models.Model):
    group_code   = models.CharField(max_length=50, unique=True, db_index=True)
    description  = models.CharField(max_length=255)
    esg_category = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Material Group Map'

    def __str__(self):
        return f"{self.group_code} - {self.esg_category}"


class GridEmissionFactor(models.Model):
    """
    Grid emission factors. Scoped to Organisation — each company can
    override with their own verified factors.
    """
    # ── Tenant scope ──────────────────────────────────────────────────────────
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='grid_emission_factors',
        db_index=True,
    )

    country          = models.CharField(max_length=100, db_index=True)
    year             = models.SmallIntegerField(db_index=True)
    factor_kg_per_kwh = models.DecimalField(max_digits=10, decimal_places=6)
    source           = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name    = 'Grid Emission Factor'
        # Unique per org + country + year
        unique_together = [('organisation', 'country', 'year')]

    def __str__(self):
        return f"{self.country} {self.year}: {self.factor_kg_per_kwh} kgCO2e/kWh"


class AirportLookup(models.Model):
    """
    IATA airport codes. Scoped to Organisation (allows custom additions).
    """
    # ── Tenant scope ──────────────────────────────────────────────────────────
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='airport_lookups',
        db_index=True,
    )

    iata    = models.CharField(max_length=4, db_index=True)
    name    = models.CharField(max_length=255, blank=True)
    city    = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=3, blank=True)
    lat     = models.DecimalField(max_digits=9, decimal_places=6)
    lon     = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        db_table        = 'lookup_airport'
        verbose_name    = 'Airport Lookup'
        unique_together = [('organisation', 'iata')]

    def __str__(self):
        return f"{self.iata} - {self.city}"


class TravelEmissionFactor(models.Model):
    """
    Emission factors for travel segments. Scoped to Organisation.
    """
    # ── Tenant scope ──────────────────────────────────────────────────────────
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='travel_emission_factors',
        db_index=True,
    )

    category          = models.CharField(max_length=20, db_index=True)
    sub_type          = models.CharField(max_length=30, null=True, blank=True)
    cabin_class       = models.CharField(max_length=20, null=True, blank=True)
    car_category      = models.CharField(max_length=30, null=True, blank=True)
    fuel_type         = models.CharField(max_length=20, null=True, blank=True)
    region            = models.CharField(max_length=10, null=True, blank=True)
    rail_carrier      = models.CharField(max_length=100, null=True, blank=True)
    factor_kg_per_unit = models.DecimalField(max_digits=10, decimal_places=6)
    unit_description  = models.CharField(max_length=100, blank=True)
    source            = models.CharField(max_length=100, blank=True)
    vintage_year      = models.IntegerField(null=True, blank=True)
    rfi_included      = models.BooleanField(default=False)

    class Meta:
        db_table     = 'lookup_travel_emission_factor'
        verbose_name = 'Travel Emission Factor'

    def __str__(self):
        return (
            f"{self.category}"
            f"/{self.cabin_class or self.sub_type or self.fuel_type or self.region or self.rail_carrier}"
            f": {self.factor_kg_per_unit}"
        )
