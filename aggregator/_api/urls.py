from django.urls import path

from aggregator._api.views import (MatchPsychologistsAjaxView,
                                   PublicPsychologistListView)
from aggregator.apps import AggregatorConfig

app_name = AggregatorConfig.name

urlpatterns = [
    path("psychologists/", PublicPsychologistListView.as_view(), name="psychologists"),

    # AJAX-запрос (fetch) для моментальной фильтрации психологов по указанным клиентом критериям на html-странице
    path("match-psychologists/", MatchPsychologistsAjaxView.as_view(), name="ajax-match-psychologists"),
]
