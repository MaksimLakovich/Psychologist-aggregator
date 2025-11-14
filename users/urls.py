from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.apps import UsersConfig
from users.views import (CustomTokenObtainPairView, EmailVerificationView,
                         RegisterView)

app_name = UsersConfig.name

urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("register/psychologist/", RegisterView.as_view(), name="register-psychologist"),
    path("register/client/", RegisterView.as_view(), name="register-client"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify-email"),
]
