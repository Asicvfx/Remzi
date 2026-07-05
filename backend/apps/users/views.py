from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.users.serializers import (
    RegisterSerializer,
    RemziTokenObtainPairSerializer,
    UserSerializer,
)
from apps.users.services import RegisterUserService


@extend_schema_view(
    post=extend_schema(
        summary="Register a new user",
        description="Creates a Remzi account and returns the created user payload.",
    )
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        serializer.instance = RegisterUserService.execute(
            validated_data=serializer.validated_data.copy()
        )


@extend_schema(
    summary="Login and obtain JWT tokens",
    description="Returns access and refresh tokens for a valid username/password pair.",
)
class RemziTokenObtainPairView(TokenObtainPairView):
    serializer_class = RemziTokenObtainPairSerializer


@extend_schema(
    summary="Get current user profile",
    description="Returns the authenticated user's profile data.",
)
class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
