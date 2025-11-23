from django.urls import path, include
from users.apps import UsersConfig

app_name = UsersConfig.name

urlpatterns = [
    # API (DRF)
    path("", include("users._api.urls", namespace="api")),

    # WEB (обычные Django views + шаблоны)
    # path("", include("users._web.urls", namespace="web")),
]
