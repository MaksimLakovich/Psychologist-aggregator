from rest_framework import serializers

from calendar_engine.booking.use_cases.therapy_session_create import \
    CreateTherapySessionUseCase
from calendar_engine.models import CalendarEvent, EventParticipant, TimeSlot
from users.constants import PREFERRED_TOPIC_TYPE_CHOICES

# =====
# СЕССИИ МЕЖДУ КЛИЕНТОМ И СПЕЦИАЛИСТОМ
# =====


# 1) Создание обычного разового события (терапевтическая сессия)

class CreateTherapySessionSerializer(serializers.Serializer):
    """Serializer для API-сценария создания встречи между клиентом и специалистом (терапевтическая сессия).

    На текущем этапе это тонкая HTTP-обертка над CreateTherapySessionUseCase, чтобы web-flow и API использовали
    одну и ту же бизнес-логику."""

    specialist_profile_id = serializers.IntegerField()
    slot_start_iso = serializers.CharField()
    consultation_type = serializers.ChoiceField(choices=PREFERRED_TOPIC_TYPE_CHOICES)

    def create(self, validated_data):
        """Запускает CreateTherapySessionUseCase от имени текущего request.user."""
        request = self.context["request"]
        use_case = CreateTherapySessionUseCase()

        return use_case.execute(
            client_user=request.user,
            specialist_profile_id=validated_data["specialist_profile_id"],
            slot_start_iso=validated_data["slot_start_iso"],
            consultation_type=validated_data["consultation_type"],
        )


# 2) Просмотр списка событий (используется вложенность сериализаторов)

class EventSlotSerializer(serializers.ModelSerializer):
    """Получение СЛОТА(-ОВ) внутри события.
    Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализации в DRF на
    основе модели TimeSlot. Нужен для GET-ответа, чтобы клиент API видел все временные интервалы события,
    если в будущем событие станет составным и будет включать несколько слотов."""

    # TimeZoneField в Python это объект "zoneinfo.ZoneInfo", а ZoneInfo не JSON-serializable, поэтому сериализатор
    # его не переведет JSON и получим ошибку, поэтому нужно явно описать поле timezone в сериализаторе.
    timezone = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    cancel_reason_type_display = serializers.CharField(
        source="get_cancel_reason_type_display",
        read_only=True,
    )

    class Meta:
        model = TimeSlot
        fields = [
            "id",
            "start_datetime",
            "end_datetime",
            "status",
            "status_display",
            "timezone",
            "meeting_url",
            "comment",
            "meeting_resume",
            "cancel_reason_type",
            "cancel_reason_type_display",
            "cancel_reason",
            "slot_index",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EventParticipantSerializer(serializers.ModelSerializer):
    """Получение УЧАСТНИКА(-ОВ) внутри события.
    Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализации в DRF на
    основе модели EventParticipant. Нужен для GET-ответа, чтобы клиент API видел состав участников,
    их роли и текущие статусы внутри события."""

    full_name = serializers.SerializerMethodField()  # поле заполняется методом get_имя_поля
    avatar_url = serializers.SerializerMethodField()  # поле заполняется методом get_имя_поля
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = EventParticipant
        fields = [
            "user_id",
            "full_name",
            "avatar_url",
            "role",
            "role_display",
            "status",
            "status_display",
            "joined_at",
            "left_at",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        """Метод возвращает безопасное имя участника без показа email в первом приоритете."""
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full_name

    def get_avatar_url(self, obj):
        """Метод возвращает фото участника, если оно доступно, либо системную аватарку по умолчанию."""
        return obj.user.avatar_url


class EventListSerializer(serializers.ModelSerializer):
    """События для GET-выдачи списка.
    Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализации в DRF на
    основе модели CalendarEvent. Нужен для чтения уже созданных встреч/событий текущего пользователя,
    чтобы API возвращал не только технический id события, но и весь базовый состав данных для интерфейсов."""

    creator = serializers.StringRelatedField(read_only=True)
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    visibility_display = serializers.CharField(source="get_visibility_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    counterpart = serializers.SerializerMethodField()  # поле заполняется методом get_имя_поля
    participants = EventParticipantSerializer(many=True, read_only=True)  # Вложенный сериализатор
    recurrence_frequency = serializers.SerializerMethodField()  # поле заполняется методом get_имя_поля
    recurrence_frequency_display = serializers.SerializerMethodField()  # поле заполняется методом get_имя_поля
    slots = EventSlotSerializer(many=True, read_only=True)  # Вложенный сериализатор

    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "creator",
            "title",
            "description",
            "event_type",
            "event_type_display",
            "status",
            "status_display",
            "visibility",
            "visibility_display",
            "source",
            "source_display",
            "is_recurring",
            "counterpart",
            "recurrence_frequency",
            "recurrence_frequency_display",
            "participants",
            "slots",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_counterpart(self, obj):
        """Метод возвращает второго участника события относительно текущего пользователя.

        Бизнес-смысл:
            - в терапевтической сессии клиенту важно быстро понять, с каким именно специалистом создана встреча;
            - поэтому в списке дополнительно отдаем компактную сводку по "другой стороне" события,
              а не заставляем фронт вычислять это самостоятельно из массива participants.
        """
        request = self.context.get("request")
        current_user = getattr(request, "user", None)

        counterpart_participant = next(
            (
                participant
                for participant in obj.participants.all()
                if not current_user or participant.user_id != current_user.pk
            ),
            None,
        )
        # # 1. Создаем переменную, где будем хранить результат (пока там пусто)
        # counterpart_participant = None
        #
        # # 2. Перебираем всех участников в цикле
        # for participant in obj.participants.all():
        #
        #     # 3. Если текущего пользователя нет ИЛИ ID участника не совпадает с ID пользователя
        #     if not current_user or participant.user_id != current_user.pk:
        #
        #         # 4. Сохраняем этого участника и прерываем цикл (мы нашли кого искали)
        #         counterpart_participant = participant
        #         break

        if not counterpart_participant:
            return None

        counterpart_user = counterpart_participant.user
        counterpart_full_name = f"{counterpart_user.first_name} {counterpart_user.last_name}".strip()

        try:
            specialist_profile = counterpart_user.psychologist_profile
            specialist_profile_id = specialist_profile.pk
        except Exception:
            specialist_profile_id = None

        return {
            "user_id": str(counterpart_user.pk),
            "full_name": counterpart_full_name,
            "avatar_url": counterpart_user.avatar_url,
            "specialist_profile_id": specialist_profile_id,
        }

    def get_recurrence_frequency(self, obj):
        """Метод возвращает техническое значение периодичности повторения, если правило повторения уже существует."""
        recurrence = next(iter(obj.recurrences.all()), None)
        return recurrence.frequency if recurrence else None

    def get_recurrence_frequency_display(self, obj):
        """Метод возвращает человекочитаемую периодичность события.

        Бизнес-смысл:
            - если правило повторения у события не создано - то это обычная разовая встреча;
            - когда позже будет подключен полноценный recurrence-flow, API сразу начнет возвращать
              корректное display-значение без изменения контракта для других повторяющихся событий.
        """
        recurrence = next(iter(obj.recurrences.all()), None)
        return recurrence.get_frequency_display() if recurrence and recurrence.frequency else "Разовая встреча"
