from rest_framework import serializers

from calendar_engine.booking.use_cases.therapy_session_create import \
    CreateTherapySessionUseCase
from users.constants import PREFERRED_TOPIC_TYPE_CHOICES

# =====
# ТЕРАПЕВТИЧЕСКИЕ СЕССИИ МЕЖДУ КЛИЕНТОМ И СПЕЦИАЛИСТОМ
# =====


class CreateTherapySessionSerializer(serializers.Serializer):
    """Serializer для API-сценария создания встречи между клиентом и специалистом (терапевтическая сессия).

    На текущем этапе это тонкая HTTP-обертка над CreateTherapySessionUseCase,
    чтобы web-flow и API использовали одну и ту же бизнес-логику.
    """

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
