from django.urls import include, path

from users.apps import UsersConfig

app_name = UsersConfig.name

urlpatterns = [
    # API (DRF)
    path("api/", include("users._api.urls", namespace="api")),

    # WEB (обычные Django views + шаблоны)
    path("", include("users._web.urls", namespace="web")),
]
