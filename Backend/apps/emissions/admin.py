from django.contrib import admin
from .models import PlantLookup


@admin.register(PlantLookup)
class PlantLookupAdmin(admin.ModelAdmin):
    list_display = [
        'werks_code', 'plant_name', 'city', 'country',
        'region', 'plant_type', 'default_scope', 'is_active', 'added_by',
    ]
    list_filter   = ['country', 'region', 'plant_type', 'is_active']
    search_fields = ['werks_code', 'plant_name', 'city']
    readonly_fields = ['id', 'added_by', 'created_at', 'updated_at']
    ordering      = ['country', 'werks_code']
    fieldsets = (
        ('SAP Identifier', {
            'fields': ('id', 'werks_code', 'plant_name', 'plant_type'),
        }),
        ('Location', {
            'fields': ('address_line', 'city', 'state', 'country', 'postal_code'),
        }),
        ('Emissions Classification', {
            'fields': ('region', 'default_scope', 'grid_emission_factor'),
        }),
        ('Status & Notes', {
            'fields': ('is_active', 'notes'),
        }),
        ('Audit', {
            'fields': ('added_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
