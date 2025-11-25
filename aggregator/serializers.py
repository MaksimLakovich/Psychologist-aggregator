class PsychologistProfileListSerializer(serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе моделей AppUser и PsychologistProfile. Описывает, какие поля АККАУНТА/ПРОФИЛЯ будут участвовать в
    сериализации/десериализации данных при создании *Публичного каталога психологов*."""

    methods = MethodSerializer(read_only=True, many=True)
    topics = TopicSerializer(read_only=True, many=True)
    educations = serializers.SerializerMethodField()  # забираем записи из модели Education по creator (AppUser)

    class Meta:
        model = PsychologistProfile
        fields = [
            "user__first_name",
            "user__last_name",
            # "user__age",
            # "user__timezone",
            "photo",
            "methods",
            "topics",
            "educations",
            "biography",
            # "gender",
            # "languages",
            # "therapy_format",
            # "work_status",
            # "rating",
            "work_experience",
            "price_individual",
            "price_couples",
        ]

    def get_educations(self, obj):
        """Получаем из модели Education записи текущего психолога."""
        user = obj.user
        return EducationSerializer(
            Education.objects.filter(creator=user).order_by("-year_start"),
            many=True
        ).data