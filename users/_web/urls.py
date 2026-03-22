from django.contrib.auth.views import LogoutView
from django.urls import path

from users._web.views.auth_view import (LoginPageView, RegisterPageView,
                                        VerifyEmailView)
from users._web.views.change_password_view import ChangePasswordPageView
from users._web.views.edit_client_view import EditClientProfilePageView
from users._web.views.reset_password_view import (PasswordResetConfirmPageView,
                                                  PasswordResetRequestPageView)
from users.apps import UsersConfig

app_name = UsersConfig.name

urlpatterns = [
    # Регистрация / Авторизация / Выход / Подтверждения
    path("login/", LoginPageView.as_view(), name="login-page"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterPageView.as_view(), name="register-page"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),

    # Работа с аккаунтом / Работа с профилем
    path("password-reset/", PasswordResetRequestPageView.as_view(), name="password-reset"),
    path("password-reset-confirm/", PasswordResetConfirmPageView.as_view(), name="password-reset-confirm"),
    path("password-change/", ChangePasswordPageView.as_view(), name="password-change"),
    path("profile-edit/", EditClientProfilePageView.as_view(), name="profile-edit"),
]
