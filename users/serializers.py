from rest_framework import serializers

from users.mixins.creator_mixin import CreatorMixin
from users.models import (AppUser, ClientProfile, Education, Method,
                          PsychologistProfile, Specialisation, Topic)


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
            "id",
            "creator",
            "country",
            "institution",
            "degree",
            "specialisation",
            "year_start",
            "year_end",
            "document",
            "is_verified",
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


class AppUserSerializer(serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе модели AppUser. Описывает, какие поля из AppUser будут участвовать в сериализации/десериализации."""

    class Meta:
        model = AppUser
        # Лучше не использовать fields = "__all__" потому что с "__all__" наш API отдаст все поля,
        # включая is_staff, is_superuser и т.п. Это опасно, потому что через API можно будет
        # назначить себе суперправа.
        fields = ["uuid", "email", "first_name", "last_name", "age", "phone_number", "role", "timezone", "password"]
        read_only_fields = ["uuid", "is_staff", "is_superuser", "is_active", "last_login", "created_at", "updated_at"]
        # extra_kwargs - это зарезервированное имя в Meta-классе ModelSerializer для настройки конкретных полей,
        # например, ниже указываю что пароль только на ЗАПИСЬ. Т.е. его можно отправить через POST/PUT/PATCH,
        # но оно не будет отображаться в ответе API (GET, LIST и т.п.).
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        """Метод для переопределения создания пользователя, чтобы пароль сохранялся в БД в захэшированном виде."""
        password = validated_data.pop("password")
        user = AppUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        """Метод полностью блокирует password при выполнении update, чтоб пароль менялся только через
         отдельный дополнительный эндпоинт с хешированием пароля."""
        if "password" in validated_data:
            raise serializers.ValidationError(
                {"password": "Пароль нельзя изменять через update. Используйте существующий метод смены пароля."}
            )
        return super().update(instance, validated_data)


class PsychologistProfileSerializer(serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе модели PsychologistProfile. Описывает, какие поля из PsychologistProfile будут участвовать в
    сериализации/десериализации."""

    user = AppUserSerializer(read_only=True)
    specialisations = SpecialisationSerializer(read_only=True, many=True)
    methods = MethodSerializer(read_only=True, many=True)
    topics = TopicSerializer(read_only=True, many=True)
    educations = EducationSerializer(read_only=True, many=True)

    class Meta:
        model = PsychologistProfile
        fields = [
            "id",
            "user",
            "gender",
            "specialisations",
            "methods",
            "topics",
            "educations",
            "biography",
            "photo",
            "rating",
            "work_experience",
            "languages",
            "therapy_format",
            "price_individual",
            "price_couples",
            "work_status",
        ]
        read_only_fields = [
            "id", "user", "is_verified", "is_all_education_verified", "rating", "created_at", "updated_at"
        ]


class ClientProfileSerializer(serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе ClientProfile. Описывает, какие поля из ClientProfile будут участвовать в сериализации/десериализации."""

    user = AppUserSerializer(read_only=True)
    preferred_methods = MethodSerializer(read_only=True, many=True)
    requested_topics = TopicSerializer(read_only=True, many=True)

    class Meta:
        model = ClientProfile
        fields = ["id", "user", "therapy_experience", "preferred_methods", "requested_topics"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


    # class UserObtainPairSerializer(TokenObtainPairSerializer):
    #     """Кастомный класс-сериализатор токена наследующийся от *TokenObtainPairSerializer*, позволяющий вход по email."""
    #
    #     # ВАЖНО! Необходимо указать, что username_field - это будет email.
    #     # До это мы указывали в модели это "USERNAME_FIELD = "email"" но это настройка Django, например, в админке,
    #     # логике логина, командах createsuperuser и т.п. Но это не влияет на процессы DRF. Логика сериализатора от
    #     # DRF Simple JWT НЕ смотрит на USERNAME_FIELD модели автоматически. Поэтому чтобы Simple JWT понял, что логин
    #     # должен быть по email, а не по username, нужно явно указать это в сериализаторе в username_field
    #     username_field = AppUser.EMAIL_FIELD
    #
    #     def validate(self, attrs):
    #         """Валидация данных при получении токена: проверка существования пользователя и корректности пароля."""
    #         # Получаю email и password из тела запроса
    #         email = attrs.get("email")
    #         password = attrs.get("password")
    #
    #         if email and password:  # ШАГ 1: проверяю все ли данные есть
    #             try:  # ШАГ 2: Ищу пользователя с таким email
    #                 user = AppUser.objects.get(email=email)
    #             except AppUser.DoesNotExist:
    #                 raise AuthenticationFailed("Пользователь с таким email не найден.")
    #
    #             if not user.check_password(password):  # ШАГ 3: Проверяю пароль
    #                 raise AuthenticationFailed("Неверный пароль.")
    #
    #         else:
    #             raise AuthenticationFailed("Необходимо указать email и пароль.")
    #
    #         # ШАГ 4: Если все ок, то формирую словарь, чтобы передать в родительский "validate()"
    #         data = super().validate(
    #             {
    #                 self.username_field: user.email,  # Ключ "email", значение - email пользователя
    #                 "password": password,
    #             }
    #         )
    #         # ШАГ 5: Добавляю еще данные в ответ (опционально, это полезно для будущего функционала)
    #         data["email"] = user.email
    #         data["user_id"] = user.id
    #
    #         return data
