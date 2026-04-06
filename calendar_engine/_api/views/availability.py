from datetime import datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.views import View
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from calendar_engine._api.serializers.availability import (
    AvailabilityExceptionSerializer, AvailabilityRuleSerializer)
from calendar_engine.application.factories.generate_specialist_schedule_factory import \
    build_generate_specialist_schedule_use_case
from calendar_engine.application.use_cases.get_domain_slots_use_case import \
    GetDomainSlotsUseCase
from calendar_engine.models import AvailabilityException, AvailabilityRule
from core.services.anonymous_client_flow_for_search_and_booking import \
    build_guest_profile
from users.models import PsychologistProfile
from users.permissions import IsPsychologistOrAdmin

# =====
# РАБОЧИЙ ГРАФИК ПСИХОЛОГА
# =====


class AvailabilityRuleListCreateView(generics.ListCreateAPIView):
    """Класс-контроллер на основе Generic для управления рабочим расписанием специалиста.

    Возможности:
    1) GET (200_OK):
        - по умолчанию возвращает только активное правило (is_active=True)
        - include_archived=true -> возвращает все правила (включая архивные)
    2) POST (201_CREATED):
        - создает новое правило доступности (рабочее расписание)
        - при создании нового автоматически деактивируется предыдущее активное правило
        - автоматически проставляет creator и timezone
    """

    permission_classes = [IsAuthenticated, IsPsychologistOrAdmin]
    serializer_class = AvailabilityRuleSerializer

    def get_queryset(self):
        """Возвращает правила доступности текущего пользователя. По умолчанию - только активное правило."""
        user = self.request.user
        include_archived = self.request.query_params.get("include_archived")

        queryset = (
            AvailabilityRule.objects
            .filter(creator=user)
            .prefetch_related("time_windows")
        )

        if include_archived not in ("true", "1", "yes"):
            queryset = queryset.filter(is_active=True)

        return queryset.order_by("-created_at")

    @transaction.atomic  # Отвечает за то, чтоб итоговое сохранение произошло только при успешном завершении всех шагов
    def perform_create(self, serializer):
        """Метод для создания нового рабочего расписания.
        Алгоритм:
            1) деактивировать текущее активное правило (если есть)
            2) создать новое правило как is_active=True
            3) timezone берется из профиля пользователя"""
        user = self.request.user

        # Ищем существующее активное правило и деактивируем его перед сохранением нового правила
        # (у специалиста может быть только 1 активное правило)
        AvailabilityRule.objects.filter(
            creator=user,
            is_active=True,
        ).update(is_active=False)

        serializer.save(
            timezone=getattr(user, "timezone", None),
            is_active=True,
        )


class AvailabilityRuleDeactivateView(APIView):
    """Класс-контроллер на основе APIView для явного "закрытия" рабочего расписания специалиста.

    Возможности:
    1) PATCH:
        - по умолчанию возвращает только активное правило (is_active=True)
        - soft-delete: вместо DESTROY-запроса (устанавливаем is_active=False).
    """

    permission_classes = [IsAuthenticated, IsPsychologistOrAdmin]

    def patch(self, request, *args, **kwargs):
        """Soft-delete для явного "закрытия" рабочего расписания специалиста: помечаем is_active=False."""
        user = request.user

        rule = AvailabilityRule.objects.filter(
            creator=user,
            is_active=True,
        ).first()

        if not rule:
            return Response(
                data={"detail": "Активное рабочее расписание не найдено"},
                status=status.HTTP_404_NOT_FOUND
            )

        rule.is_active = False
        rule.save(update_fields=["is_active"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class AvailabilityExceptionListCreateView(generics.ListCreateAPIView):
    """Класс-контроллер на основе Generic для управления исключениями в рабочем расписании специалиста.

    Возможности:
    1) GET (200_OK):
        - по умолчанию возвращает только активные исключения (is_active=True)
        - include_archived=true -> возвращает все исключения (включая архивные)
    2) POST (201_CREATED):
        - создает новое исключение из рабочего расписания
        - автоматическая привязка исключения к действующему AvailabilityRule(is_active=True)
        - автоматически проставляет creator
    """

    permission_classes = [IsAuthenticated, IsPsychologistOrAdmin]
    serializer_class = AvailabilityExceptionSerializer

    def get_queryset(self):
        """Возвращает исключения из рабочего расписания. По умолчанию - только активные исключения."""
        user = self.request.user
        include_archived = self.request.query_params.get("include_archived")

        queryset = (
            AvailabilityException.objects
            .filter(creator=user)
            .select_related("rule")
            .prefetch_related("time_windows")
        )

        if include_archived not in ("true", "1", "yes"):
            queryset = queryset.filter(is_active=True)

        return queryset.order_by("-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        """Метод для создания нового исключения в рабочем расписании.
        Алгоритм:
            1) создать новое исключение как is_active=True
            2) автоматическая привязка исключения к действующему AvailabilityRule(is_active=True)
            3) автоматически проставляет creator"""
        user = self.request.user

        # Ищем существующее активное правило
        rule = AvailabilityRule.objects.filter(
            creator=user,
            is_active=True,
        ).first()

        if not rule:
            raise NotFound(
                {"Активное рабочее расписание не найдено"}
            )

        serializer.save(
            rule=rule,
            is_active=True,
        )


class AvailabilityExceptionDeactivateView(APIView):
    """Класс-контроллер на основе APIView для явного "закрытия" исключения из расписания специалиста. В реальной жизни:
        - больничный отменили
        - отпуск сократили
        - day-off перенесли

    Возможности:
    1) PATCH:
        - применяется только к действующим активным исключениям (is_active=True)
        - soft-delete: вместо DESTROY-запроса (устанавливаем is_active=False).
    """

    permission_classes = [IsAuthenticated, IsPsychologistOrAdmin]

    def patch(self, request, *args, **kwargs):
        """Soft-delete для явного "закрытия" исключения из рабочего расписания специалиста: is_active=False."""
        user = request.user

        exception = get_object_or_404(
            AvailabilityException,
            creator=user,
            pk=kwargs["pk"],
            is_active=True,
        )

        exception.is_active = False
        exception.save(update_fields=["is_active"])

        return Response(status=status.HTTP_204_NO_CONTENT)


# =====
# ВСЕ ВОЗМОЖНЫЕ ДОМЕННЫЕ СЛОТЫ + СЛОТЫ ОТФИЛЬТРОВАННЫЕ НА ОСНОВЕ РАБОЧЕГО РАСПИСАНИЯ СПЕЦИАЛИСТА
# =====


def _resolve_schedule_viewer_context(request) -> tuple[object, str | None]:
    """Возвращает viewer-user и preferred-consultation-type для чтения/просмотра schedule-preview специалистов.

    Почему здесь нельзя использовать get_client_profile_for_request(...):
        - этот helper по смыслу и по реализации предназначен именно для client-flow;
        - на catalog/detail-экраны теперь могут заходить и другие роли, например psychologist и гость;
        - у psychologist/admin нет client_profile, поэтому schedule-preview специалиста должен уметь работать
          без client-profile, опираясь только на timezone текущего пользователя и на consultation_type из query.

    Контракт:
        - guest-anonymous -> берем временный guest-profile из session;
        - авторизованный client -> используем request.user и его preferred_topic_type из client_profile;
        - любой другой авторизованный пользователь -> используем request.user, а preferred-consultation-type
          не подставляем (fallback произойдет позже до 'individual').
    """
    if request.user.is_authenticated:
        user = request.user
        try:
            preferred_consultation_type = user.client_profile.preferred_topic_type
        except ObjectDoesNotExist:
            preferred_consultation_type = None
        return user, preferred_consultation_type

    guest_profile = build_guest_profile(request.session)
    return guest_profile.user, guest_profile.preferred_topic_type


class GetDomainSlotsAjaxView(View):
    """Возвращает клиенту на UI все возможные доменные временные слоты (общее правило домена).
    Read-only эндпоинт только для показа возможных слотов на странице пользователя, без сохранения в БД.

    Работает с двумя сценариями:
        - сценарий 1: работает зарегистрированный авторизованный пользователь;
        - сценарий 2: работает guest-anonymous.
    """

    def get(self, request, *args, **kwargs):
        """Получить все доменные временные слоты."""
        # Для чтения/просмотра schedule-preview специалиста достаточно timezone текущего viewer'а.
        # Важно: здесь поддерживаем не только client/guest, но и psychologist/admin, которые тоже могут открыть
        # каталог и фильтры по времени.
        viewer_user, _ = _resolve_schedule_viewer_context(request)

        use_case = GetDomainSlotsUseCase(
            timezone=viewer_user.timezone
        )

        result = use_case.execute()

        # ВАЖНО: кроме сгенерированных слотов (slots) нам необходимо передать на фронт еще текущее время
        # пользователя (now_iso), потому что определять его по времени сервера неправильно. Так как клиент в
        # настройках своего профиля указывает свой timezone и он может отличаться от сервера (путешествует например).
        # ОБОСНОВАНИЕ: текущее время пользователя нам необходимо для того, чтоб потом на странице деактивировать
        # слоты, которые уже в прошлом (делать их недоступными к выбору).
        return JsonResponse(
            data={
                "status": "ok",
                "now_iso": result["now_iso"],
                "slots": result["slots"],
            },
            status=200,
        )


class GetSpecialistScheduleAjaxView(View):
    """Возвращает viewer'у на UI в карточке конкретного специалиста актуальное расписание данного специалиста:
        - ближайший доступный слот;
        - все доступные слоты в блоке "Расписание".

    Все слоты ОТОБРАЖЕНЫ в TZ текущего viewer'а.
    Read-only эндпоинт только для показа доступных слотов из расписания специалиста, без сохранения в БД.

    Работает с тремя сценариями:
        - сценарий 1: работает guest-anonymous;
        - сценарий 2: работает авторизованный client;
        - сценарий 3: работает авторизованный psychologist/admin.
    """

    def get(self, request, *args, **kwargs):
        """Получить расписание специалиста (доступные слоты) в TZ текущего viewer'а.

        Важно: используем 'consultation_type', который нужен для понимания того, какой тип сессии будем
        использовать при расчете доступности специалиста.
        Пример:
            - рабочее окно специалиста: 06:00–08:00
            - session_duration_individual = 50
            - session_duration_couple = 120
        Тогда:
            - старт 06:00 для individual допустим, потому что сессия закончится в 06:50
            - старт 07:00 для individual тоже допустим, потому что сессия закончится в 07:50
            - старт 06:00 для couple еще допустим, потому что закончится в 08:00
            - старт 07:00 для couple уже НЕДОПУСТИМ, потому что сессия выйдет за границу рабочего окна.
        Т.е., без consultation_type система не может понять, какой именно duration проверять для этого расписания.
        """
        viewer_user, preferred_consultation_type = _resolve_schedule_viewer_context(request)

        profile_id = kwargs["profile_id"]
        consultation_type = request.GET.get("consultation_type")
        # Когда клиент открывает модалку “Перенести встречу”, фронт запрашивает у backend доступные слоты специалиста.
        # Но есть нюанс:
        # - старая встреча еще существует в БД и она уже занимает время у специалиста;
        # - если просто построить расписание "как есть", backend посчитает, что это время занято и старая встреча
        # начнет блокировать перенос сама на себя
        exclude_event_id = request.GET.get("exclude_event_id")
        # Эта вьюха берет profile_id из kwargs и далее использует specialist_profile.user, поэтому нужно
        # использовать get_object_or_404() и передавать именно объект дальше
        specialist_profile = get_object_or_404(PsychologistProfile, pk=profile_id)

        def normalize_tz(tz_value):
            """Безопасный fallback на 'timezone=None'.
            Просто 'ZoneInfo(str(specialist_profile.user.timezone))' превратит None в 'None' и выбросит исключение.
            Поэтому нужна безопасная ветка: если timezone None - fallback на now() без astimezone."""
            if tz_value is None:
                return None
            if isinstance(tz_value, tzinfo):
                return tz_value
            return ZoneInfo(str(tz_value))

        viewer_tz = normalize_tz(getattr(viewer_user, "timezone", None))
        specialist_tz = normalize_tz(getattr(specialist_profile.user, "timezone", None)) or viewer_tz

        if consultation_type not in ("individual", "couple"):
            consultation_type = preferred_consultation_type or "individual"

        use_case = build_generate_specialist_schedule_use_case(
            specialist_profile=specialist_profile,
            consultation_type=consultation_type,
            exclude_event_ids=[exclude_event_id] if exclude_event_id else None,
        )

        if use_case is None:
            return JsonResponse(
                {
                    "status": "ok",
                    "nearest_slot": None,
                    "schedule": [],
                },
                status=200,
            )

        slots = use_case.execute()

        # ВАЖНО: кроме сгенерированного расписания нам необходимо передать на фронт еще текущее время
        # viewer'а (now_iso_client) и текущее время специалиста (now_iso_specialist), потому что определять
        # его по времени сервера неправильно. Так как viewer/специалист в настройках своего профиля
        # указывает свой timezone и он может отличаться от сервера (путешествует например).
        # ОБОСНОВАНИЕ: полезно для отладки и тестирования.
        now_client = now().astimezone(viewer_tz) if viewer_tz else now()
        now_specialist = now().astimezone(specialist_tz) if specialist_tz else now()

        # Use-case генерирует слоты в TZ специалиста, но ответ должен быть в TZ текущего viewer'а.
        # Изначально отправляется raw SlotDTO, так что клиент увидит время специалиста.
        # Нужна конвертация: локализовать (day+start_time) в TZ специалиста и перевести в TZ viewer'а,
        # затем отдать ISO/строку.
        schedule = []

        for slot in slots:
            if specialist_tz:
                slot_start_spec = datetime.combine(slot.day, slot.start, tzinfo=specialist_tz)
                slot_end_spec = datetime.combine(slot.day, slot.end, tzinfo=specialist_tz)
            else:
                slot_start_spec = datetime.combine(slot.day, slot.start)
                slot_end_spec = datetime.combine(slot.day, slot.end)

            # Если слот пересекает полночь (например, 23:00–00:00), конец нужно сдвигать на следующий день,
            # так как 00:00 это уже +1
            if slot.end <= slot.start:
                slot_end_spec += timedelta(days=1)

            if slot_start_spec < now_specialist:
                continue

            slot_start_client = (
                slot_start_spec.astimezone(viewer_tz)
                if viewer_tz
                else slot_start_spec
            )
            slot_end_client = (
                slot_end_spec.astimezone(viewer_tz)
                if viewer_tz
                else slot_end_spec
            )

            # schedule возвращает как SlotDTO, который не JSON‑serializable поэтому нужен перевод в ISO datetime
            schedule.append(
                {
                    "day": slot_start_client.date().isoformat(),
                    "start_time": slot_start_client.strftime("%H:%M"),
                    "end_time": slot_end_client.strftime("%H:%M"),
                    "start_iso": slot_start_client.isoformat(),
                    "end_iso": slot_end_client.isoformat(),
                }
            )

        nearest_slot = schedule[0] if schedule else None

        return JsonResponse(
            {
                "status": "ok",
                "nearest_slot": nearest_slot,
                "schedule": schedule,
                "now_iso_client": now_client.isoformat(),
                "now_iso_specialist": now_specialist.isoformat(),
            },
            status=200,
        )
