"""
apps/organisations/views.py — fixed for DRF auth timing

All views now use core.tenant.get_active_organisation(request) to read
org from the JWT directly rather than from middleware-set user attributes.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions import IsTenantAdmin, IsTenantAnalyst
from core.tenant import get_active_organisation, get_active_role
from .models import Organisation, OrganisationMembership
from .serializers import (
    OrganisationSerializer,
    MembershipSerializer,
    InviteMemberSerializer,
    SwitchOrganisationSerializer,
)


class OrganisationMeView(APIView):
    """GET /api/v1/organisations/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = get_active_organisation(request)
        if not org:
            return Response(
                {"error": "You are not a member of any organisation. Contact your admin."},
                status=status.HTTP_403_FORBIDDEN,
            )
        data = OrganisationSerializer(org).data
        data["your_role"] = get_active_role(request)
        return Response(data)


class MemberListView(APIView):
    """GET /api/v1/organisations/members/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = get_active_organisation(request)
        if not org:
            return Response([], status=200)
        memberships = (
            OrganisationMembership.objects
            .filter(organisation=org, is_active=True)
            .select_related("user")
            .order_by("role", "user__email")
        )
        return Response(MembershipSerializer(memberships, many=True).data)


class InviteMemberView(APIView):
    """POST /api/v1/organisations/members/invite/"""
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request):
        serializer = InviteMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        from apps.users.models import User
        email = serializer.validated_data["email"]
        role  = serializer.validated_data["role"]
        org   = get_active_organisation(request)

        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "role": role},
        )
        if user_created:
            temp_pw = f"BreatheESG@{org.slug}!"
            user.set_password(temp_pw)
            user.save()

        membership, mem_created = OrganisationMembership.objects.get_or_create(
            organisation=org, user=user,
            defaults={"role": role, "is_active": True},
        )
        if not mem_created:
            if membership.is_active:
                return Response(
                    {"error": f"{email} is already a member of {org.name}."},
                    status=status.HTTP_409_CONFLICT,
                )
            membership.is_active = True
            membership.role = role
            membership.save()

        return Response({
            "message":      f"{email} has been added to {org.name} as {role}.",
            "user_created": user_created,
            "membership":   MembershipSerializer(membership).data,
        }, status=status.HTTP_201_CREATED)


class MemberDetailView(APIView):
    """PATCH / DELETE /api/v1/organisations/members/{id}/"""
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def _get_membership(self, pk, org):
        try:
            return OrganisationMembership.objects.get(pk=pk, organisation=org)
        except OrganisationMembership.DoesNotExist:
            return None

    def patch(self, request, pk):
        org        = get_active_organisation(request)
        membership = self._get_membership(pk, org)
        if not membership:
            return Response({"error": "Member not found."}, status=status.HTTP_404_NOT_FOUND)

        new_role = request.data.get("role")
        if new_role not in OrganisationMembership.Role.values:
            return Response(
                {"error": f"Invalid role. Choices: {OrganisationMembership.Role.values}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership.role = new_role
        membership.save()
        return Response(MembershipSerializer(membership).data)

    def delete(self, request, pk):
        org        = get_active_organisation(request)
        membership = self._get_membership(pk, org)
        if not membership:
            return Response({"error": "Member not found."}, status=status.HTTP_404_NOT_FOUND)

        if membership.user == request.user:
            return Response(
                {"error": "You cannot remove yourself from the organisation."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership.is_active = False
        membership.save()
        return Response({"message": "Member removed from organisation."}, status=status.HTTP_200_OK)


class SwitchOrganisationView(APIView):
    """GET / POST /api/v1/organisations/switch/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            OrganisationMembership.objects
            .filter(user=request.user, is_active=True)
            .select_related("organisation")
        )
        current_org = get_active_organisation(request)
        result = []
        for m in memberships:
            result.append({
                "organisation_id":   str(m.organisation.id),
                "organisation_name": m.organisation.name,
                "organisation_slug": m.organisation.slug,
                "role":              m.role,
                "is_current":        current_org and m.organisation.id == current_org.id,
            })
        return Response(result)

    def post(self, request):
        serializer = SwitchOrganisationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        org_id = serializer.validated_data["organisation_id"]
        try:
            membership = OrganisationMembership.objects.select_related("organisation").get(
                user=request.user, organisation_id=org_id, is_active=True,
            )
        except OrganisationMembership.DoesNotExist:
            return Response({"error": "You are not a member of that organisation."}, status=status.HTTP_403_FORBIDDEN)

        # Issue a new JWT with updated org claims
        refresh = RefreshToken.for_user(request.user)
        refresh["organisation_id"]   = str(membership.organisation.id)
        refresh["organisation_name"] = membership.organisation.name
        refresh["organisation_slug"] = membership.organisation.slug
        refresh["role"]              = membership.role

        return Response({
            "message":      f"Switched to {membership.organisation.name}.",
            "access":       str(refresh.access_token),
            "refresh":      str(refresh),
            "organisation": OrganisationSerializer(membership.organisation).data,
            "role":         membership.role,
        })
