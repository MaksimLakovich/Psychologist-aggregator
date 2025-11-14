from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.apps import UsersConfig
from users.views import (CustomTokenObtainPairView, EmailVerificationView,
                         RegisterView, ResendEmailVerificationView)

app_name = UsersConfig.name

urlpatterns = [
    path("register/psychologist/", RegisterView.as_view(), name="register-psychologist"),
    path("register/client/", RegisterView.as_view(), name="register-client"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify-email"),
    path("resend-verify-email/", ResendEmailVerificationView.as_view(), name="resend-verify-email"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
