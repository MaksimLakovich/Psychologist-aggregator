from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from calendar_engine._api.serializers.events import CreateTherapySessionSerializer
from calendar_engine.booking.exceptions import CreateTherapySessionValidationError
from calendar_engine.booking.throttles import CreateTherapySessionThrottle


class CalendarTherapySessionListCreateView(GenericAPIView):
    """API-endpoint для клиента по выполнению им сценария создания встречи со специалистом
    (терапевтическая сессия) - CreateTherapySession."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [CreateTherapySessionThrottle]
    serializer_class = CreateTherapySessionSerializer

    def post(self, request, *args, **kwargs):
        """Создает встречу (терапевтическая сессия) через CreateTherapySessionUseCase и возвращает ответ."""
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
