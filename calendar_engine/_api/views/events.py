from django.db.models import Min, Prefetch, Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from calendar_engine._api.serializers.events import (
    CreateTherapySessionSerializer, EventListSerializer)
from calendar_engine.booking.exceptions import \
    CreateTherapySessionValidationError
from calendar_engine.booking.throttles import CreateTherapySessionThrottle
from calendar_engine.models import (CalendarEvent, EventParticipant,
                                    RecurrenceRule, TimeSlot)


class CalendarEventListCreateView(generics.ListCreateAPIView):
    """Класс-контроллер на основе Generic для работы с событиями клиента.

    Возможности:
    1) GET (200_OK):
        - по умолчанию возвращает только актуальные события текущего пользователя (статус = planned/started);
        - include_archived=true - возвращает все события пользователя, включая завершенные/отмененные.
    2) POST (201_CREATED):
        - создает новую терапевтическую сессию через CreateTherapySessionUseCase;
        - использует тот же бизнес-сценарий, что и web-flow на странице оплаты.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [CreateTherapySessionThrottle]

    def get_serializer_class(self):
        """Метод возвращает определенный serializer под определенный запрос:
            - для создания новой терапевтической сессии - CreateTherapySessionSerializer;
            - для получения списка всех видов сессий - EventListSerializer.
        """
        if self.request.method == "POST":
            return CreateTherapySessionSerializer
        return EventListSerializer

    def get_throttles(self):
        """Throttle нужен только на создание.

        Бизнес-смысл:
            - GET-список клиент может открывать часто, например при обновлении кабинета или работе мобильного UI;
            - ограничивать здесь частоту запросов не нужно;
            - а вот POST создает реальные встречи, поэтому для него антиспам-защита обязательна.
        """
        if self.request.method == "POST":
            return [throttle() for throttle in self.throttle_classes]  # Сейчас у нас 1, но это конструкция на будущее
        return []

    def get_queryset(self):
        """Возвращает все виды событий текущего пользователя.

        Бизнес-смысл:
            - endpoint называется events/, поэтому сюда будут попадать все типы календарных событий (терапевтические
              сессии, курсы, вебинары и т.д);
            - по умолчанию клиенту нужен список именно актуальных встреч, а архив подгружается отдельно
              через include_archived=true.
        """
        user = self.request.user
        include_archived = self.request.query_params.get("include_archived")

        queryset = (
            CalendarEvent.objects
            .filter(
                participants__user=user,
            )
            .prefetch_related(
                Prefetch(
                    "participants",
                    queryset=EventParticipant.objects.select_related("user").order_by("created_at"),
                ),
                Prefetch(
                    "slots",
                    queryset=TimeSlot.objects.order_by("start_datetime", "slot_index"),
                ),
                Prefetch(
                    "recurrences",
                    queryset=RecurrenceRule.objects.filter(is_active=True).order_by("created_at"),
                ),
            )
            .distinct()
        )

        if include_archived not in ("true", "1", "yes"):
            queryset = queryset.filter(status__in=["planned", "started"]).annotate(
                first_relevant_slot_start=Min(
                    "slots__start_datetime",
                    filter=Q(slots__status__in=["planned", "started"]),
                )
            ).order_by("first_relevant_slot_start", "-created_at")
        else:
            queryset = queryset.annotate(
                first_relevant_slot_start=Min("slots__start_datetime")
            ).order_by("-created_at")

        return queryset

    def create(self, request, *args, **kwargs):
        """Создает встречу (терапевтическую сессию) через CreateTherapySessionUseCase и возвращает ответ."""
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        try:
            booking_result = serializer.save()
        except CreateTherapySessionValidationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "event_id": str(booking_result["event"].id),
                "slot_id": str(booking_result["slot"].id),
                "status": booking_result["event"].status,
            },
            status=status.HTTP_201_CREATED,
        )
