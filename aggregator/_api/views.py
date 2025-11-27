from django.db.models import Prefetch
from django_filters import rest_framework as filters
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from aggregator._api.filters import PsychologistFilter
from aggregator._api.serializers import PublicPsychologistListSerializer
from aggregator.paginators import PsychologistCatalogPagination
from users.models import Education, PsychologistProfile


class PublicPsychologistListView(generics.ListAPIView):
    """Класс-контроллер на основе Generic для взаимодействия авторизованных пользователей системы
     с *Публичным каталогом психологов*:
        - отображение карточек психологов (только верифицированные и активные);
        - фильтрация результатов поиска (topics/methods/gender);
        - пагинация страницы с результатами;
        - prefetch Education без N+1."""

    permission_classes = [IsAuthenticated]
    serializer_class = PublicPsychologistListSerializer
    pagination_class = PsychologistCatalogPagination

    # Настройка фильтрации (пакет: poetry add django-filter)
    filter_backends = (filters.DjangoFilterBackend,)  # Бэкенд для обработки фильтра
    # filterset_fields = ("topics", "methods", "gender")  # Набор полей для фильтрации без filterset_class
    filterset_class = PsychologistFilter  # Набор полей для фильтрации указан в кастомном FilterSet

    def get_queryset(self):
        """Получение набора данных, который будет использоваться во View (оптимизирован под нагруженные каталоги).
        1) Выводим только активных и верифицированных психологов.
        2) Для того, чтоб избежать проблемы N+1 используем: select_related + prefetch_related, иначе выдача
        будет очень медленной из-за того, что API без этого будет дергать: отдельно user, methods и topics.
        3) Для того, чтоб избежать проблемы N+1 с Education используем: Prefetch() и для этого мы по-особенному
        определили метод get_educations() в сериализаторе PublicPsychologistListSerializer."""
        return (
            PsychologistProfile.objects
            .filter(is_verified=True, user__is_active=True)
            .select_related("user")
            .prefetch_related(
                "methods", "topics",
                Prefetch(
                    lookup="user__created_educations",
                    queryset=Education.objects.order_by("-year_start"),
                    to_attr="prefetched_educations",
                )
            )
            # Временно сортируем по id (позже можно добавить любое другой ранжирование, которое реализуем)
            .order_by("id")
        )
