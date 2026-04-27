from django.db.models import Prefetch
from django.http import JsonResponse
from django.views import View
from django_filters import rest_framework as filters
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from aggregator._api.filters import PsychologistFilter
from aggregator._api.serializers import PublicPsychologistListSerializer
from aggregator._web.services.final_aggregator import \
    PsychologistAggregatorService
from aggregator._web.services.topic_type_mapping import \
    CLIENT_TO_TOPIC_TYPE_MAP
from aggregator.paginators import PsychologistCatalogPagination
from calendar_engine.application.mappers.match_result_mapper import \
    map_match_result_to_dict
from calendar_engine.models import AvailabilityRule
from core.services.experience_label import build_experience_label
from core.services.get_client_profile_for_request import \
    get_client_profile_for_request
from core.services.session_duration_label import attach_session_duration_labels
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
                    lookup="user__availability_rules",
                    queryset=AvailabilityRule.objects.filter(is_active=True).order_by("-created_at"),
                    to_attr="prefetched_active_availability_rules",
                ),
                Prefetch(
                    lookup="user__created_educations",
                    queryset=Education.objects.order_by("-year_start"),
                    to_attr="prefetched_educations",
                )
            )
            # Временно сортируем по id (позже можно добавить любое другой ранжирование, которое реализуем)
            .order_by("id")
        )


class MatchPsychologistsAjaxView(View):
    """Класс-контроллер на основе View для автоматического запуска фильтрации психологов без кнопки "Далее"
    по указанным клиентом:
        - интересующих его базовым параметрам: темы, методы, возраст, пол;
        - интересующих его временным слотам.

    Решение: AJAX-запрос (fetch) на специальный API-endpoint.

    Контроллер работает по двум сценариям:
        - сценарий 1: работает зарегистрированный авторизованный пользователь;
        - сценарий 2: работает guest-anonymous.
    """

    def get(self, request, *args, **kwargs):
        """Метод для запуска фильтрации и возврата JSON-контракта с готовыми данными для карточки психолога.

        get_client_profile_for_request(request) - возвращает профиль, с которым дальше должен работать matching-flow:
            - если клиент уже авторизован, то используется реальный ClientProfile из БД;
            - если клиент еще гость, то используется session и временный профиль гостя.
        """
        try:
            client_profile = get_client_profile_for_request(request)
        except Exception:
            return JsonResponse({"error": "no_client_profile"}, status=400)

        # ШАГ 1: Создаем и запускаем АГРЕГАТОР с процессом фильтрации психологов по заданным клиентом параметрам

        aggregator = PsychologistAggregatorService(client_profile)
        aggregated_results = aggregator.get_aggregated_results()

        # ШАГ 2: Формируем для каждого отфильтрованного психолога JSON с детальными данными для карточки психолога.
        # Для инфо: JsonResponse не умеет сериализовать QuerySet, поэтому нужно из QuerySet сделать подходящий
        # список словарей (собственно нужный нам JSON)

        data = []
        preferred_topic_type = client_profile.preferred_topic_type  # Для определения цены (individual / couple)

        for item in aggregated_results.values():
            ps = item["profile"]
            attach_session_duration_labels(ps)
            availability = item["availability"]  # MatchResultDTO | None

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
                "topic_score": ps.topic_score,
                "method_score": ps.method_score,
                "full_name": f"{ps.user.first_name} {ps.user.last_name}".strip(),
                "photo": ps.photo.url if ps.photo else "/static/images/menu/user-circle.svg",
                "session_type": preferred_topic_type,
                "price": {
                    "value": str(price_value),
                    "currency": ps.price_currency,
                },
                "price_individual": str(ps.price_individual),
                "price_couples": str(ps.price_couples),
                "price_currency": ps.price_currency,
                "session_duration_individual": ps.session_duration_individual_minutes,
                "session_duration_couple": ps.session_duration_couple_minutes,
                "session_duration_individual_label": ps.session_duration_individual_label,
                "session_duration_couple_label": ps.session_duration_couple_label,
                "work_experience": ps.work_experience_years,
                "experience_label": build_experience_label(ps.work_experience_years),
                "rating": ps.rating,
                "biography": ps.biography,
                "educations": educations_data,
                "methods": methods_data,
                "matched_topics": matched_topics_data,
                "timezone": str(ps.user.timezone) if ps.user.timezone else None,
                "schedule": (
                    map_match_result_to_dict(availability)
                    if availability
                    else {"status": "no_match"}
                ),
            })

        return JsonResponse({"items": data})
