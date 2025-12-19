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
from aggregator._web.services.topic_type_mapping import \
    CLIENT_TO_TOPIC_TYPE_MAP
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
        """Метод для запуска фильтрации и возврата JSON-контракта с готовыми данными для карточки психолога."""
        user = request.user

        try:
            client_profile = user.client_profile
        except Exception:
            return JsonResponse({"error": "no_client_profile"}, status=400)

        # ШАГ 1: Запускаем процесс фильтрации психологов по заданным клиентом параметрам
        qs = match_psychologists(client_profile)

        # ШАГ 2: Формируем для каждого отфильтрованного психолога JSON с детальными данными для карточки психолога.
        # Для инфо: JsonResponse не умеет сериализовать QuerySet, поэтому нужно из QuerySet сделать подходящий
        # список словарей (собственно нужный нам JSON)

        data = []

        preferred_topic_type = client_profile.preferred_topic_type  # Для определения цены (individual / couple)

        for ps in qs:

            # Цена
            price_value = (
                ps.price_couples
                if preferred_topic_type == "couple"
                else ps.price_individual
            )

            # Образование
            educations = Education.objects.filter(creator=ps.user).order_by("-year_start")

            educations_data = [
                {
                    "year_start": edu.year_start,
                    "year_end": edu.year_end,
                    "institution": edu.institution,
                    "specialisation": edu.specialisation,
                }
                for edu in educations
            ]

            # Методы
            methods_data = [
                {
                    "id": method.id,
                    "name": method.name,
                    "description": method.description,
                }
                for method in ps.methods.all()
            ]

            # Совпавшие темы
            # ВАЖНЫЕ МОМЕНТ: используем явный mapping-слой (адаптер) между полем TYPE в таблице public.users_topic (где
            # указано "Индивидуальная"/"Парная" на русском языке) и полем PREFERRED_TOPIC_TYPE в таблице
            # public.users_clientprofile (где указано "Individual"/"Couple" на английском)
            mapped_topic_type = CLIENT_TO_TOPIC_TYPE_MAP.get(preferred_topic_type)

            requested_topic_ids = client_profile.requested_topics.filter(
                type=mapped_topic_type
            ).values_list("id", flat=True)

            matched_topic_ids = set(
                ps.topics.filter(
                    id__in=requested_topic_ids,
                    type=mapped_topic_type,
                ).values_list("id", flat=True)
            )

            matched_topics_data = [
                {
                    "id": topic.id,
                    "type": topic.type,
                    "group_name": topic.group_name,
                    "name": topic.name,
                }
                for topic in ps.topics.filter(id__in=matched_topic_ids)
            ]

            # Формируем итоговый контракт
            data.append({
                "id": ps.id,
                "full_name": f"{ps.user.first_name} {ps.user.last_name}".strip(),
                "photo": ps.photo.url if ps.photo else "/static/images/menu/user-circle.svg",
                "price": {
                    "value": str(price_value),
                    "currency": ps.price_currency,
                },
                "work_experience": ps.work_experience_years,
                "rating": ps.rating,
                "biography": ps.biography,
                "educations": educations_data,
                "methods": methods_data,
                "matched_topics": matched_topics_data,
                "timezone": str(ps.user.timezone) if ps.user.timezone else None,
                "schedule": {
                    "status": "stub"
                }
            })

        return JsonResponse({"items": data})
