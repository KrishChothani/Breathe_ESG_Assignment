from rest_framework import serializers
from .models import SAPRow, UtilityRow, TravelRow, PlantLookup
from django.db.models import Count, Min


# ── Existing row serializers ──────────────────────────────────────────────────

class SAPRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = SAPRow
        fields = '__all__'

class UtilityRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilityRow
        fields = '__all__'

class TravelRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelRow
        fields = '__all__'


# ── PlantLookup serializers ───────────────────────────────────────────────────

class PlantLookupSerializer(serializers.ModelSerializer):
    added_by_name        = serializers.SerializerMethodField()
    unresolved_sap_rows  = serializers.SerializerMethodField()

    class Meta:
        model = PlantLookup
        fields = [
            'id', 'werks_code', 'plant_name',
            'address_line', 'city', 'state', 'country', 'postal_code',
            'region', 'plant_type', 'default_scope',
            'grid_emission_factor', 'is_active',
            'notes', 'added_by', 'added_by_name',
            'unresolved_sap_rows',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'added_by', 'created_at', 'updated_at']

    def get_added_by_name(self, obj):
        if obj.added_by:
            return f"{obj.added_by.first_name} {obj.added_by.last_name}".strip() or obj.added_by.username
        return None

    def get_unresolved_sap_rows(self, obj):
        return SAPRow.objects.filter(
            plant_code=obj.werks_code,
            plant_name=''
        ).count()


class PlantLookupCreateSerializer(serializers.ModelSerializer):
    """Used for single create and PATCH edit."""

    class Meta:
        model = PlantLookup
        fields = [
            'werks_code', 'plant_name',
            'address_line', 'city', 'state', 'country', 'postal_code',
            'region', 'plant_type', 'default_scope',
            'grid_emission_factor', 'is_active', 'notes',
        ]

    def validate_werks_code(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("WERKS code cannot be empty.")
        if len(value) > 10:
            raise serializers.ValidationError("WERKS code cannot exceed 10 characters.")
        # Uniqueness is enforced per-organisation by the DB unique_together constraint.
        # We do a soft check here using the organisation from the request context.
        request = self.context.get('request')
        if request and hasattr(request.user, 'active_organisation') and request.user.active_organisation:
            org = request.user.active_organisation
            qs  = PlantLookup.objects.filter(organisation=org, werks_code=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"WERKS code '{value}' already exists in your organisation."
                )
        return value

    def validate_country(self, value):
        value = value.strip().upper()
        if len(value) != 2:
            raise serializers.ValidationError(
                "Country must be a 2-letter ISO code e.g. IN, DE, GB, US"
            )
        return value


class PlantLookupBulkCSVSerializer(serializers.Serializer):
    file               = serializers.FileField()
    overwrite_existing = serializers.BooleanField(default=False)


class UnresolvedWERKSSerializer(serializers.Serializer):
    plant_code      = serializers.CharField()
    row_count       = serializers.IntegerField()
    first_seen      = serializers.DateField(allow_null=True)
    sample_material = serializers.CharField(allow_null=True)
