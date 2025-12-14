from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.http import JsonResponse
from django.views import View
from django_filters import rest_framework as filters
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from aggregator._api.filters import PsychologistFilter
from aggregator._api.serializers import PublicPsychologistListSerializer
from aggregator._web.services.filter_service import match_psychologists
from aggregator.paginators import PsychologistCatalogPagination
from users.models import Education, PsychologistProfile
from users.permissions import IsProfileOwnerOrAdminMixin


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


class MatchPsychologistsAjaxView(LoginRequiredMixin, IsProfileOwnerOrAdminMixin, View):
    """Класс-контроллер на основе View для автоматического запуска фильтрации психологов без кнопки "Далее"
    по указанным клиентом интересующих его параметрам (темы, методы, возраст, пол), как это делают
    профессиональные SaaS-сервисы. Решение: AJAX-запрос (fetch) на специальный API-endpoint."""

    def get(self, request, *args, **kwargs):
        """Метод для запуска процесса фильтрации."""
        user = request.user

        try:
            client_profile = user.client_profile
        except Exception:
            return JsonResponse({"error": "no_client_profile"}, status=400)

        qs = match_psychologists(client_profile)
        # JsonResponse не умеет сериализовать QuerySet, поэтому нужно из QuerySet сделать подходящий
        # список словарей, который сами сформируем, например:
        data = [
            {
                "photo": ps.photo.url if ps.photo else "/static/images/menu/user-circle.svg",
                "email": ps.user.email,
                "topic_score": ps.topic_score,
                "matched_topics_count": ps.matched_topics_count,
                "method_score": ps.method_score,
                "matched_methods_count": ps.matched_methods_count
            }
            for ps in qs
        ]

        return JsonResponse({"items": data})
