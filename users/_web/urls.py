from django.contrib.auth.views import LogoutView
from django.urls import path

from users._web.views.auth_view import (LoginPageView, RegisterPageView,
                                        VerifyEmailView)
from users.apps import UsersConfig

app_name = UsersConfig.name

urlpatterns = [
    # Регистрация / Авторизация / Выход / Подтверждения
    path("login/", LoginPageView.as_view(), name="login-page"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterPageView.as_view(), name="register-page"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),

    # Работа с аккаунтом / Работа с профилем
]
