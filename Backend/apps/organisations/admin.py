from django.contrib import admin
from .models import Organisation, OrganisationMembership


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'industry', 'country', 'subscription_plan', 'is_active', 'created_at')
    list_filter   = ('subscription_plan', 'is_active', 'country')
    search_fields = ('name', 'slug', 'industry')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(OrganisationMembership)
class OrganisationMembershipAdmin(admin.ModelAdmin):
    list_display  = ('user', 'organisation', 'role', 'is_active', 'joined_at')
    list_filter   = ('role', 'is_active', 'organisation')
    search_fields = ('user__email', 'user__username', 'organisation__name')
    raw_id_fields = ('user', 'organisation')
