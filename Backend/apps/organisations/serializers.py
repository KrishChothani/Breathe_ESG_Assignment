from rest_framework import serializers
from .models import Organisation, OrganisationMembership
from apps.users.models import User


class OrganisationSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model  = Organisation
        fields = [
            'id', 'name', 'slug', 'industry', 'country',
            'subscription_plan', 'is_active', 'member_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class MembershipSerializer(serializers.ModelSerializer):
    user_email     = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    user_id        = serializers.UUIDField(source='user.id', read_only=True)

    class Meta:
        model  = OrganisationMembership
        fields = [
            'id', 'user_id', 'user_email', 'user_full_name',
            'role', 'is_active', 'joined_at',
        ]
        read_only_fields = ['id', 'user_id', 'user_email', 'user_full_name', 'joined_at']

    def get_user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role  = serializers.ChoiceField(choices=OrganisationMembership.Role.choices)

    def validate_email(self, value):
        return value.lower().strip()


class SwitchOrganisationSerializer(serializers.Serializer):
    organisation_id = serializers.UUIDField()
