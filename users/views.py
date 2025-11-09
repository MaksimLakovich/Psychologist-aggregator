from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from users.serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """Класс-контроллер на основе TokenObtainPairView для авторизации по email."""

    permission_classes = [AllowAny]  # type: ignore[assignment]
    serializer_class = CustomTokenObtainPairSerializer
