from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.views import (
    CurrentUserView,
    PasswordChangeView,
    RegisterView,
    UserAccessUpdateView,
    UserListView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("password/", PasswordChangeView.as_view(), name="password-change"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/access/", UserAccessUpdateView.as_view(), name="user-access-update"),
]
