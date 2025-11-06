from rest_framework import serializers

from users.mixins.creator_mixin import CreatorMixin
from users.models import Specialisation, Topic


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
