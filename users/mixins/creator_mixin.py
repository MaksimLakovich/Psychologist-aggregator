from rest_framework import serializers


class CreatorMixin(serializers.ModelSerializer):
    """Миксин, который автоматически заполняет поле creator текущим пользователем при создании или обновлении."""

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["creator"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["creator"] = request.user
        return super().update(instance, validated_data)
