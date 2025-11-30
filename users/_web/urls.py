from django.urls import path

from users._web.views.auth_view import AppUserLoginView
from users.apps import UsersConfig

app_name = UsersConfig.name

urlpatterns = [
    path("login/", AppUserLoginView.as_view(), name="login_page"),
]
