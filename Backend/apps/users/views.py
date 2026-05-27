from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import UserSerializer, TenantTokenObtainPairSerializer


class TenantLoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Replaces simplejwt's default TokenObtainPairView.
    Returns JWT with organisation_id and role embedded in claims.
    """
    serializer_class = TenantTokenObtainPairSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)
