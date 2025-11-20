from rest_framework import serializers


class CreatorMixin(serializers.ModelSerializer):
    """Миксин, который автоматически заполняет поле creator текущим пользователем при создании объекта."""

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["creator"] = request.user
        return super().create(validated_data)
