from django.urls import include, path

from calendar_engine.apps import AppCalendarConfig

app_name = AppCalendarConfig.name

urlpatterns = [
    # API (DRF + AJAX)
    path("calendar/api/", include("calendar_engine._api.urls", namespace="api")),

    # WEB (обычные Django views + шаблоны)
    path("", include("calendar_engine._web.urls", namespace="web")),
]