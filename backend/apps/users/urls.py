from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import CurrentUserView, RegisterView, RemziTokenObtainPairView


app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", RemziTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", CurrentUserView.as_view(), name="me"),
]
