class PsychologistProfileListView(generics.ListAPIView):
    """Класс-контроллер на основе Generic для взаимодействия пользователей с *Публичным каталогом психологов*:
        - отображение карточек психологов (только верифицированные и активные);
        - фильтрация результатов поиска;
        - пагинация страницы с результатами."""

    permission_classes = [IsAuthenticated]
    serializer_class = PsychologistProfileListSerializer
    pagination_class = PsychologistCatalogPagination

    def get_queryset(self):
        """Получение набора данных, который будет использоваться во View."""
        return PsychologistProfile.objects.filter(is_verified=True, user__is_active=True)

