from django.urls import include, path

from aggregator.apps import AggregatorConfig

app_name = AggregatorConfig.name

urlpatterns = [
    # API (DRF)
    path("catalog/api/", include("aggregator._api.urls", namespace="api")),

    # WEB (обычные Django views + шаблоны)
    # path("", include("aggregator._web.urls", namespace="web")),
]
