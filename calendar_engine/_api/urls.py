from django.urls import path

from calendar_engine._api.views.availability import (AvailabilityExceptionDeactivateView,
                                                     AvailabilityExceptionListCreateView,
                                                     AvailabilityRuleDeactivateView,
                                                     AvailabilityRuleListCreateView,
                                                     GetDomainSlotsAjaxView,
                                                     GetSpecialistScheduleAjaxView)
from calendar_engine.apps import AppCalendarConfig

app_name = AppCalendarConfig.name

urlpatterns = [
    # Рабочее расписание психолога
    path(
        "my-availability-rules/", AvailabilityRuleListCreateView.as_view(), name="availability-rules-list-create"
    ),
    path(
        "my-availability-rules/close/", AvailabilityRuleDeactivateView.as_view(), name="availability-rules-close"
    ),
    path(
        "my-availability-exceptions/",
        AvailabilityExceptionListCreateView.as_view(),
        name="availability-exceptions-list-create"
    ),
    path(
        "my-availability-exceptions/<int:pk>/close/",
        AvailabilityExceptionDeactivateView.as_view(),
        name="availability-exceptions-close"
    ),

    # AJAX-запрос (fetch) на создание и отображение временных слотов и расписания на html-страницах
    path("get-domain-slots/", GetDomainSlotsAjaxView.as_view(), name="get-domain-slots"),
    path(
        "psychologists/<int:profile_id>/schedule/",
        GetSpecialistScheduleAjaxView.as_view(),
        name="get-psychologist-schedule"
    ),
]
