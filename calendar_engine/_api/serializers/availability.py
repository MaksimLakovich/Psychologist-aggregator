from datetime import time

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from calendar_engine.models import (AvailabilityException,
                                    AvailabilityExceptionTimeWindow,
                                    AvailabilityRule,
                                    AvailabilityRuleTimeWindow)

# =====
# РАБОЧИЙ ГРАФИК ПСИХОЛОГА
# =====


class AvailabilityRuleTimeWindowSerializer(serializers.ModelSerializer):
    """Временное окно доступности специалиста внутри рабочего дня в AvailabilityRule (например, "с 09:00 до 18:00").
    Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализации в DRF на
    основе модели AvailabilityRuleTimeWindow. Описывает, какие поля из AvailabilityRuleTimeWindow будут
    участвовать в сериализации/десериализации."""

    class Meta:
        model = AvailabilityRuleTimeWindow
        fields = [
            "id",
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        """Метод для кастомной валидации ВРЕМЕНИ начала/окончания правила."""
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        if not (start_time and end_time):
            raise ValidationError(
                "Параметры start_time и end_time обязательны при создании рабочего правила"
            )

        if start_time and end_time:

            if start_time == end_time and start_time != time(0, 0):
                raise ValidationError(
                    "Параметры start_time и end_time могут совпадать только для 24/7 (00:00–00:00)"
                )

            elif start_time > end_time:
                raise ValidationError("Параметр start_time должен быть меньше end_time")

        return attrs


# CreatorMixin на уровне класса мы не можем использовать уже, как делали в других сериализаторах, потому что
# в классе мы создали метод create(), который переопределяет логику - миксин можно использовать только без create()
class AvailabilityRuleSerializer(serializers.ModelSerializer):
    """Рабочее расписание специалиста (правило доступности, например: Пн-Пт, с набором рабочих окон внутри дня).
    Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализации в DRF на
    основе модели AvailabilityRule. Описывает, какие поля из AvailabilityRule будут участвовать в
    сериализации/десериализации."""

    creator = serializers.StringRelatedField(read_only=True)
    available_windows = AvailabilityRuleTimeWindowSerializer(
        many=True,
        source="time_windows",
        required=True,  # нельзя создать правило без временного окна
    )
    # TimeZoneField в Python это объект "zoneinfo.ZoneInfo", а ZoneInfo не JSON-serializable, поэтому сериализатор
    # его не переведет JSON и получим ошибку, поэтому нужно явно описать поле timezone в сериализаторе
    timezone = serializers.CharField(read_only=True)

    class Meta:
        model = AvailabilityRule
        fields = [
            "id",
            "creator",
            "timezone",
            "rule_start",
            "rule_end",
            "weekdays",
            "available_windows",
            "slot_duration",
            "break_between_sessions",
            "minimum_booking_notice_hours",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "creator", "timezone", "is_active", "created_at", "updated_at"]

    def validate_weekdays(self, value):
        """Метод для кастомной валидации поля weekdays."""
        if not value:
            raise ValidationError("Нужно указать хотя бы один рабочий день недели")

        return value

    def validate(self, attrs):
        """Метод для кастомной валидации ДАТЫ начала/окончания правила."""
        rule_start = attrs.get("rule_start")
        rule_end = attrs.get("rule_end")
        windows_data = self.initial_data.get("available_windows")
        # Используя initial_data мы получаем сырые данные (еще до сериализации), а можно было бы
        # реализовать validated_data - очищенные и типизированные данные.
        # Но в нашем случае initial_data - это ОК, потому что: мы проверяем лишь факт наличия / отсутствия,
        # а не структуру данных.

        if rule_start and rule_end and rule_start > rule_end:
            raise ValidationError("Дата в rule_start должна быть раньше даты в rule_end")

        if not windows_data:
            raise ValidationError("Параметры start_time и end_time обязательны при создании рабочего правила")

        return attrs

    def create(self, validated_data):
        """Метод для создания ВРЕМЕННОГО ОКНА доступности в правиле."""
        windows_data = validated_data.pop("time_windows", [])
        rule = AvailabilityRule.objects.create(
            creator=self.context["request"].user,
            **validated_data,
        )

        for window_data in windows_data:
            AvailabilityRuleTimeWindow.objects.create(
                rule=rule,
                **window_data,
            )

        return rule

    def update(self, instance, validated_data):
        """Метод для обновления существующего ВРЕМЕННОГО ОКНА доступности в правиле."""
        windows_data = validated_data.pop("time_windows", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if windows_data is not None:
            instance.time_windows.all().delete()

            for window_data in windows_data:
                AvailabilityRuleTimeWindow.objects.create(
                    rule=instance,
                    **window_data,
                )

        return instance


class AvailabilityExceptionTimeWindowSerializer(serializers.ModelSerializer):
    """Переопределенное временное окно доступности внутри рабочего дня из AvailabilityException.
    Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализации в DRF на
    основе модели AvailabilityExceptionTimeWindow. Описывает, какие поля из AvailabilityExceptionTimeWindow будут
    участвовать в сериализации/десериализации."""

    class Meta:
        model = AvailabilityExceptionTimeWindow
        fields = [
            "id",
            "override_start_time",
            "override_end_time",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        """Метод для кастомной валидации ПЕРЕОПРЕДЕЛЕННОГО ВРЕМЕНИ начала/окончания правила."""
        override_start_time = attrs.get("override_start_time")
        override_end_time = attrs.get("override_end_time")

        if not (override_start_time and override_end_time):
            raise ValidationError(
                "Параметры override_start_time и override_end_time обязательны при 'exception_type = override'"
            )

        if override_start_time and override_end_time:

            if override_start_time == override_end_time and override_start_time != time(0, 0):
                raise ValidationError(
                    "Параметры override_start_time и override_end_time могут совпадать только для 24/7 (00:00–00:00)"
                )

            elif override_start_time > override_end_time:
                raise ValidationError("Параметр override_start_time должен быть меньше override_end_time")

        return attrs


# CreatorMixin на уровне класса мы не можем использовать уже, как делали в других сериализаторах, потому что
# в классе мы создали метод create(), который переопределяет логику - миксин можно использовать только без create()
class AvailabilityExceptionSerializer(serializers.ModelSerializer):
    """Исключение из рабочего расписания психолога.
    Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализации в DRF на
    основе модели AvailabilityException. Описывает, какие поля из AvailabilityException будут участвовать в
    сериализации/десериализации."""

    creator = serializers.StringRelatedField(read_only=True)
    override_available_windows = AvailabilityExceptionTimeWindowSerializer(
        many=True,
        source="time_windows",
        required=False,  # можно создать исключение без временного окна (например, полностью недоступный день)
    )

    class Meta:
        model = AvailabilityException
        fields = [
            "id",
            "creator",
            "rule",
            "exception_start",
            "exception_end",
            "override_available_windows",
            "reason",
            "exception_type",
            "override_slot_duration",
            "override_break_between_sessions",
            "override_minimum_booking_notice_hours",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "creator", "is_active", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        """Ограничение rule только правилами текущего пользователя, чтоб исключить кейс с передачей rule_id
        другого специалиста."""
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            self.fields["rule"].queryset = AvailabilityRule.objects.filter(
                creator=request.user
            )

    def validate(self, attrs):
        """Метод для кастомной валидации ПЕРЕОПРЕДЕЛЕННОГО ВРЕМЕНИ начала/окончания исключения."""
        exception_type = attrs.get("exception_type")
        start = attrs.get("exception_start")
        end = attrs.get("exception_end")
        windows_data = self.initial_data.get("override_available_windows")
        # Используя initial_data мы получаем сырые данные (еще до сериализации), а можно было бы
        # реализовать validated_data - очищенные и типизированные данные.
        # Но в нашем случае initial_data - это ОК, потому что: мы проверяем лишь факт наличия / отсутствия,
        # а не структуру данных.

        if start and end and start > end:
            raise ValidationError("Параметр exception_date_start не может быть позже exception_date_end")

        if exception_type == "override":  # Частичное переопределение
            if not windows_data:
                raise ValidationError(
                    "Для exception_type='override' необходимо указать добавить переопределенное временное окно."
                )

        if exception_type == "unavailable":  # Полностью недоступен
            if windows_data:
                raise ValidationError("Для exception_type='unavailable' override_available_windows недопустимы")

            if attrs.get("override_minimum_booking_notice_hours") is not None:
                raise ValidationError(
                    "Для exception_type='unavailable' override_minimum_booking_notice_hours недопустим."
                )

        return attrs

    def create(self, validated_data):
        """Метод для создания ВРЕМЕННОГО ОКНА доступности в исключении."""
        windows_data = validated_data.pop("time_windows", [])
        exception = AvailabilityException.objects.create(
            creator=self.context["request"].user,
            **validated_data,
        )

        for window_data in windows_data:
            AvailabilityExceptionTimeWindow.objects.create(
                exception=exception,
                **window_data,
            )

        return exception

    def update(self, instance, validated_data):
        """Метод для обновления существующего ВРЕМЕННОГО ОКНА доступности в исключении."""
        windows_data = validated_data.pop("time_windows", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if windows_data is not None:
            instance.time_windows.all().delete()

            for window_data in windows_data:
                AvailabilityExceptionTimeWindow.objects.create(
                    exception=instance,
                    **window_data,
                )

        return instance
