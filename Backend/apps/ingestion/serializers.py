"""
apps/ingestion/serializers.py

Contains:
 - RawUploadSerializer         (existing)
 - All NavanXxxSerializer classes mirroring the Navan Open API importTrip schema
"""

from decimal import Decimal
from rest_framework import serializers
from .models import RawUpload


# ── Existing serializer ───────────────────────────────────────────────────────

class RawUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawUpload
        fields = '__all__'


# ── Navan shared sub-serializers ──────────────────────────────────────────────

class NavanCostSerializer(serializers.Serializer):
    amount   = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    currency = serializers.CharField(max_length=5, required=True)


class NavanAddressSerializer(serializers.Serializer):
    street     = serializers.CharField(required=False, allow_blank=True, default='')
    city       = serializers.CharField(required=False, allow_blank=True, default='')
    state      = serializers.CharField(required=False, allow_blank=True, default='')
    country    = serializers.CharField(required=False, allow_blank=True, default='')
    postalCode = serializers.CharField(required=False, allow_blank=True, default='')


class NavanTravelerSerializer(serializers.Serializer):
    email      = serializers.EmailField(required=True)
    firstName  = serializers.CharField(required=False, allow_blank=True, default='')
    lastName   = serializers.CharField(required=False, allow_blank=True, default='')
    employeeId = serializers.CharField(required=False, allow_blank=True, default='')


# ── Segment serializers ───────────────────────────────────────────────────────

CABIN_CHOICES = ['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST']
CAR_CAT_CHOICES = ['ECONOMY', 'COMPACT', 'MIDSIZE', 'STANDARD', 'FULL_SIZE', 'LUXURY', 'SUV', 'VAN']
FUEL_CHOICES = ['PETROL', 'DIESEL', 'HYBRID', 'ELECTRIC', 'UNKNOWN']
RAIL_CLASS_CHOICES = ['STANDARD', 'FIRST']
GROUND_SUBTYPE_CHOICES = ['TAXI', 'RIDESHARE', 'LIMO', 'SHUTTLE', 'BUS']


class NavanAirSegmentSerializer(serializers.Serializer):
    type                  = serializers.CharField()
    segmentId             = serializers.CharField(required=True)
    carrier               = serializers.CharField(required=False, allow_blank=True, default='')
    flightNumber          = serializers.CharField(required=False, allow_blank=True, default='')
    departureAirportCode  = serializers.CharField(required=True, max_length=10)
    arrivalAirportCode    = serializers.CharField(required=True, max_length=10)
    departureDateTime     = serializers.DateTimeField(required=True)
    arrivalDateTime       = serializers.DateTimeField(required=False, allow_null=True)
    cabinClass            = serializers.ChoiceField(
        choices=CABIN_CHOICES, required=False, default='ECONOMY', allow_blank=True
    )
    fareClass             = serializers.CharField(required=False, allow_blank=True, default='')
    numberOfPassengers    = serializers.IntegerField(required=False, default=1, min_value=1)
    cost                  = NavanCostSerializer(required=False)
    stops                 = serializers.IntegerField(required=False, default=0, min_value=0)
    operatingCarrier      = serializers.CharField(required=False, allow_blank=True, default='')
    confirmationNumber    = serializers.CharField(required=False, allow_blank=True, default='')
    ticketNumber          = serializers.CharField(required=False, allow_blank=True, default='')
    baggageAllowance      = serializers.CharField(required=False, allow_blank=True, default='')


class NavanHotelSegmentSerializer(serializers.Serializer):
    type               = serializers.CharField()
    segmentId          = serializers.CharField(required=True)
    hotelName          = serializers.CharField(required=False, allow_blank=True, default='')
    chainCode          = serializers.CharField(required=False, allow_blank=True, default='')
    checkInDate        = serializers.DateField(required=True)
    checkOutDate       = serializers.DateField(required=True)
    numberOfNights     = serializers.IntegerField(required=False, allow_null=True)
    numberOfRooms      = serializers.IntegerField(required=False, default=1, min_value=1)
    roomType           = serializers.CharField(required=False, allow_blank=True, default='')
    address            = NavanAddressSerializer(required=False)
    cost               = NavanCostSerializer(required=False)
    confirmationNumber = serializers.CharField(required=False, allow_blank=True, default='')
    loyaltyNumber      = serializers.CharField(required=False, allow_blank=True, default='')


class NavanCarSegmentSerializer(serializers.Serializer):
    type                = serializers.CharField()
    segmentId           = serializers.CharField(required=True)
    vendor              = serializers.CharField(required=False, allow_blank=True, default='')
    vendorCode          = serializers.CharField(required=False, allow_blank=True, default='')
    carCategory         = serializers.ChoiceField(choices=CAR_CAT_CHOICES, required=False, allow_blank=True, default='')
    fuelType            = serializers.ChoiceField(choices=FUEL_CHOICES, required=False, default='UNKNOWN')
    pickUpDateTime      = serializers.DateTimeField(required=True)
    dropOffDateTime     = serializers.DateTimeField(required=True)
    pickUpLocation      = NavanAddressSerializer(required=False)
    dropOffLocation     = NavanAddressSerializer(required=False)
    estimatedDistanceKm = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    cost                = NavanCostSerializer(required=False)
    confirmationNumber  = serializers.CharField(required=False, allow_blank=True, default='')


class NavanRailSegmentSerializer(serializers.Serializer):
    type                  = serializers.CharField()
    segmentId             = serializers.CharField(required=True)
    carrier               = serializers.CharField(required=True)
    trainNumber           = serializers.CharField(required=False, allow_blank=True, default='')
    departureStationCode  = serializers.CharField(required=True)
    arrivalStationCode    = serializers.CharField(required=True)
    departureDateTime     = serializers.DateTimeField(required=True)
    arrivalDateTime       = serializers.DateTimeField(required=False, allow_null=True)
    travelClass           = serializers.ChoiceField(
        choices=RAIL_CLASS_CHOICES, required=False, default='STANDARD'
    )
    numberOfPassengers    = serializers.IntegerField(required=False, default=1, min_value=1)
    cost                  = NavanCostSerializer(required=False)
    confirmationNumber    = serializers.CharField(required=False, allow_blank=True, default='')


class NavanGroundTransportSerializer(serializers.Serializer):
    type             = serializers.CharField()
    segmentId        = serializers.CharField(required=True)
    subType          = serializers.ChoiceField(
        choices=GROUND_SUBTYPE_CHOICES, required=False, allow_blank=True, default='TAXI'
    )
    provider         = serializers.CharField(required=False, allow_blank=True, default='')
    pickUpDateTime   = serializers.DateTimeField(required=True)
    dropOffDateTime  = serializers.DateTimeField(required=False, allow_null=True)
    pickUpAddress    = serializers.CharField(required=False, allow_blank=True, default='')
    dropOffAddress   = serializers.CharField(required=False, allow_blank=True, default='')
    distanceKm       = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    cost             = NavanCostSerializer(required=False)


# ── Root import-trip serializer ───────────────────────────────────────────────

class NavanImportTripSerializer(serializers.Serializer):
    """
    Validates the full importTrip body.

    segments is accepted as raw dicts so the normaliser can dispatch
    per-type validation; this keeps the API lenient enough to accept
    partial payloads and flag rather than hard-reject.
    """
    externalTripId  = serializers.CharField(required=False, allow_blank=True, default='')
    traveler        = NavanTravelerSerializer(required=True)
    tripName        = serializers.CharField(required=False, allow_blank=True, default='')
    tripDescription = serializers.CharField(required=False, allow_blank=True, default='')
    startDate       = serializers.DateField(required=False, allow_null=True)
    endDate         = serializers.DateField(required=False, allow_null=True)
    bookingSource   = serializers.CharField(required=False, allow_blank=True, default='')
    segments        = serializers.ListField(
        child=serializers.DictField(), required=True, min_length=1
    )

    def validate_segments(self, segments):
        allowed_types = {"AIR", "HOTEL", "CAR", "RAIL", "GROUND_TRANSPORT"}
        for seg in segments:
            if not isinstance(seg, dict):
                raise serializers.ValidationError(
                    "Each segment must be a JSON object."
                )
            seg_type = seg.get("type")
            if seg_type is None:
                # Allowed — normaliser will create PARSE_FAILED row
                continue
            if seg_type not in allowed_types:
                raise serializers.ValidationError(
                    f"Unknown segment type '{seg_type}'. "
                    f"Allowed: {sorted(allowed_types)}"
                )
        return segments

from django.contrib.auth import get_user_model
from apps.ingestion.models import AuditLog, RowComment

User = get_user_model()

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']

class AuditLogSerializer(serializers.ModelSerializer):
    performed_by_details = UserSimpleSerializer(source='performed_by', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'

class RowCommentSerializer(serializers.ModelSerializer):
    author_details = UserSimpleSerializer(source='author', read_only=True)
    resolved_by_details = UserSimpleSerializer(source='resolved_by', read_only=True)
    
    class Meta:
        model = RowComment
        fields = '__all__'
        read_only_fields = ['organisation', 'author', 'role_at_time', 'created_at', 'resolved_at', 'resolved_by', 'row_id', 'row_source']

