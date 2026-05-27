"""
apps/users/serializers.py
=========================
Custom JWT token serializer that injects multi-tenant claims:
  organisation_id, organisation_name, organisation_slug, role

On login:
  - If user belongs to exactly 1 active org → issue token immediately
  - If user belongs to 0 orgs → 403
  - If user belongs to >1 orgs → return list so frontend can call /switch/
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class UserSerializer(serializers.ModelSerializer):
    active_organisation = serializers.SerializerMethodField()
    active_role         = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'active_organisation', 'active_role']

    def get_active_organisation(self, obj):
        org = getattr(obj, '_active_org', None)
        if org is None:
            return None
        return {"id": str(org.id), "name": org.name, "slug": org.slug}

    def get_active_role(self, obj):
        return getattr(obj, '_active_role', obj.role)


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the standard JWT serializer to embed organisation claims.

    Returns:
      Single-org user  → { access, refresh, user, organisation, role }
      Multi-org user   → { requires_org_selection: true, organisations: [...] }
      No-org user      → raises 403
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user
        memberships = list(
            user.memberships
            .filter(is_active=True)
            .select_related("organisation")
            .order_by("organisation__name")
        )

        if not memberships:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "You are not a member of any organisation. "
                "Ask your organisation admin to invite you."
            )

        if len(memberships) > 1:
            # Frontend must call /api/v1/organisations/switch/ to pick one
            return {
                "requires_org_selection": True,
                "organisations": [
                    {
                        "organisation_id":   str(m.organisation.id),
                        "organisation_name": m.organisation.name,
                        "organisation_slug": m.organisation.slug,
                        "role":              m.role,
                    }
                    for m in memberships
                ],
            }

        # Single membership — issue token with org claims embedded
        membership = memberships[0]
        org = membership.organisation

        # Reissue tokens with custom claims
        refresh = RefreshToken.for_user(user)
        refresh["organisation_id"]   = str(org.id)
        refresh["organisation_name"] = org.name
        refresh["organisation_slug"] = org.slug
        refresh["role"]              = membership.role

        return {
            "access":  str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id":         str(user.id),
                "email":      user.email,
                "first_name": user.first_name,
                "last_name":  user.last_name,
                "username":   user.username,
            },
            "organisation": {
                "id":   str(org.id),
                "name": org.name,
                "slug": org.slug,
                "subscription_plan": org.subscription_plan,
            },
            "role": membership.role,
        }
