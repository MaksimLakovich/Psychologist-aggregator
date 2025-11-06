from rest_framework import serializers

from users.mixins.creator_mixin import CreatorMixin
from users.models import Education, Method, Specialisation, Topic


class TopicSerializer(CreatorMixin, serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе модели Topic. Описывает, какие поля из Topic будут участвовать в сериализации/десериализации."""

    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Topic
        fields = ["id", "creator", "type", "group_name", "name", "slug"]
        read_only_fields = ["id", "creator", "created_at", "updated_at"]


class SpecialisationSerializer(CreatorMixin, serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе Specialisation. Описывает, какие поля из Specialisation будут участвовать в сериализации/десериализации."""

    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Specialisation
        fields = ["id", "creator", "name", "description", "slug"]
        read_only_fields = ["id", "creator", "created_at", "updated_at"]


class MethodSerializer(CreatorMixin, serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе модели Method. Описывает, какие поля из Method будут участвовать в сериализации/десериализации."""

    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Method
        fields = ["id", "creator", "name", "description", "slug"]
        read_only_fields = ["id", "creator", "created_at", "updated_at"]


class EducationSerializer(CreatorMixin, serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе модели Education. Описывает, какие поля из Education будут участвовать в сериализации/десериализации."""

    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Education
        fields = [
            "id", "creator", "country", "institution", "degree", "specialisation",
            "year_start", "year_end", "document", "is_verified",
        ]
        read_only_fields = ["id", "creator", "created_at", "updated_at", "is_verified"]

    def validate(self, attrs):
        """Дополнительная логическая валидация полей - убедиться, что year_start <= year_end (если year_end указан)."""
        year_start = attrs.get("year_start")
        year_end = attrs.get("year_end")

        if year_start and year_end and year_end < year_start:
            raise serializers.ValidationError(
                {"year_end": "Год окончания не может быть раньше года начала."}
            )
        if year_start and year_start < 1900:
            raise serializers.ValidationError(
                {"year_start": "Некорректный год начала обучения."}
            )
        return attrs
