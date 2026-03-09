"""Пакет API views приложения calendar_engine."""

from calendar_engine._api.views.availability import (
    AvailabilityExceptionDeactivateView,
    AvailabilityExceptionListCreateView,
    AvailabilityRuleDeactivateView,
    AvailabilityRuleListCreateView,
    GetDomainSlotsAjaxView,
    GetSpecialistScheduleAjaxView,
)

__all__ = [
    "AvailabilityExceptionDeactivateView",
    "AvailabilityExceptionListCreateView",
    "AvailabilityRuleDeactivateView",
    "AvailabilityRuleListCreateView",
    "GetDomainSlotsAjaxView",
    "GetSpecialistScheduleAjaxView",
]
