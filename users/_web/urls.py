from django.contrib.auth.views import LogoutView
from django.urls import path

from users._web.views.auth_view import LoginPageView
from users.apps import UsersConfig

app_name = UsersConfig.name

urlpatterns = [
    path("login/", LoginPageView.as_view(), name="login_page"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
