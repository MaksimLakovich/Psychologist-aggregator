from rest_framework import serializers

from users._api.serializers import (MethodSerializer,
                                    PublicEducationSerializer, TopicSerializer)
from users.models import PsychologistProfile


class PublicPsychologistListSerializer(serializers.ModelSerializer):
    """Кастомный класс-сериализатор (используется только для GET) с использованием класса ModelSerializer
    для осуществления базовой сериализация в DRF на основе моделей AppUser и PsychologistProfile.
    Описывает, какие поля АККАУНТА/ПРОФИЛЯ будут участвовать в сериализации/десериализации данных при получении
    любым авторизованным пользователем системы данных из *Публичного каталога психологов*."""

    # Подтянем данные из аккаунта (модель AppUser) для данного профиля психолог:
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    age = serializers.IntegerField(source="user.age", read_only=True)
    timezone = serializers.SerializerMethodField()

    # Подтянем данные из справочников:
    methods = MethodSerializer(read_only=True, many=True)
    topics = TopicSerializer(read_only=True, many=True)
    educations = serializers.SerializerMethodField()  # забираем записи из модели Education по creator (AppUser)

    class Meta:
        model = PsychologistProfile
        fields = [
            "first_name",
            "last_name",
            "age",
            "timezone",
            "photo",
            "methods",
            "topics",
            "educations",
            "biography",
            "gender",
            "languages",
            "therapy_format",
            "work_status",
            "rating",
            "work_experience",
            "price_individual",
            "price_couples",
        ]

    def get_educations(self, obj):
        """Получаем из модели Education записи текущего психолога."""
        educations = getattr(obj.user, "prefetched_educations", [])

        return PublicEducationSerializer(educations, many=True).data

    def get_timezone(self, obj):
        """Получаем из модели AppUser запись текущего психолога о часовом поясе в виде строки для чистоты ответа."""
        return str(obj.user.timezone) if obj.user.timezone else None
