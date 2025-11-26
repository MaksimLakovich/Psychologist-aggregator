from django_filters import rest_framework as filters

from users.models import PsychologistProfile


class CSVCharFilter(filters.BaseInFilter, filters.CharFilter):
    """Кастомные 'CSV filter' для того, чтоб иметь возможность фильтровать сразу по нескольким значениям.
    Базовый CharFilter с lookup_expr="in" ожидает список (list), а не строку."""

    pass


class PsychologistFilter(filters.FilterSet):
    """Кастомный FilterSet, который укажет для фильтрации параметр slug, а не системный id."""

    topics = CSVCharFilter(field_name="topics__slug", lookup_expr="in")
    methods = CSVCharFilter(field_name="methods__slug", lookup_expr="in")
    gender = filters.CharFilter(field_name="gender")

    class Meta:
        model = PsychologistProfile
        fields = ["topics", "methods", "gender"]
