from django.urls import path

from aggregator._api.views import PublicPsychologistListView
from aggregator.apps import AggregatorConfig

app_name = AggregatorConfig.name

urlpatterns = [
    path("psychologists/", PublicPsychologistListView.as_view(), name="psychologists"),
]
