from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from users.constants import GENDER_CHOICES
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

    def update(self, obj, validated_data):
        """Метод полностью блокирует password при выполнении update, чтоб пароль менялся только через
         отдельный дополнительный эндпоинт с хешированием пароля."""
        if "password" in validated_data:
            raise serializers.ValidationError(
                {"password": "Пароль нельзя изменять через update. Используйте существующий метод смены пароля."}
            )

        return super().update(obj, validated_data)


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


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор-"оркестр" (он соединяет разные сериализаторы) для регистрации нового пользователя в системе.
    В зависимости от выбранной роли создает связанный профиль: PsychologistProfile или ClientProfile."""

    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    gender = serializers.ChoiceField(choices=GENDER_CHOICES, required=False, allow_blank=True)

    class Meta:
        model = AppUser
        fields = [
            "email",
            "first_name",
            "last_name",
            "age",
            "phone_number",
            "role",
            "timezone",
            "gender",
            "password",
            "confirm_password",
        ]
        read_only_fields = ["role",]

    def validate(self, attrs):
        """Метод для проверки совпадения паролей и базовой корректности данных регистрации."""
        password = attrs.get("password")
        # pop() делает attrs "чистыми" - т.е., получив значение он удаляет запись по ключу и оставляет в attrs
        # только те поля, которые реально принадлежат модели
        confirm_password = attrs.pop("confirm_password", None)

        # Каждый сериализатор DRF может принимать какой-либо контекст - произвольные дополнительные данные,
        # которые буду передавать вручную при создании сериализатора, например из вьюхи по регистрации:
        #     role = UserRole.objects.get(role="psychologist")
        #     serializer = RegisterSerializer(data=request.data, context={"role": role})
        # Теперь внутри сериализатора "self.context" - это словарь {"role": <UserRole: psychologist>} и можно
        # добавить проверку о том "А не забыла ли вью передать в сериализатор роль для создания профиля?" или можно
        # задать какие-либо дополнительные условия для отдельных полей (например, gender, last_name):
        role = self.context.get("role")

        if not role:
            raise serializers.ValidationError({"role": "Роль пользователя не указана."})

        if password != confirm_password:
            raise serializers.ValidationError({"password": "Пароли не совпадают."})

        if role.role == "psychologist":
            if not attrs.get("gender"):
                raise serializers.ValidationError({"gender": "Пол обязателен для психолога."})
            if not attrs.get("last_name"):
                raise serializers.ValidationError({"last_name": "Фамилия обязательна для психолога."})

        return attrs

    # @transaction.atomic - это декоратор, который оборачивает блок кода в одну транзакцию базы данных.
    # Т.е., если внутри create() произойдет любая ошибка (например, не удалось создать профиль), то:
    # 1) Django откатит все изменения;
    # 2) И в базе не останется "половинчатых" данных (например, пользователь без профиля).
    @transaction.atomic
    def create(self, validated_data):
        """Метод для создания пользователя и автоматического профиля для него в зависимости от роли."""
        password = validated_data.pop("password")
        gender = validated_data.pop("gender", "")
        role = self.context.get("role")

        # Создание пользователя
        # user = AppUser.objects.create(**validated_data, role=role)
        # лучше так, чтоб не вызывать 2 запроса к БД при создании, а делать все 1 запросом
        user = AppUser(**validated_data, role=role)
        user.set_password(password)
        user.save()

        # И сразу автоматическое создание профиля для данного пользователя
        # if role.role.lower() == "psychologist":
        #     PsychologistProfile.objects.create(user=user)
        # elif role.role.lower() == "client":
        #     ClientProfile.objects.create(user=user)
        match role.role.strip().lower():
            case "psychologist":
                PsychologistProfile.objects.create(user=user, gender=gender)
            case "client":
                ClientProfile.objects.create(user=user)

        return user

    def to_representation(self, obj):
        """Метод для настройки вывода данных после успешной регистрации."""
        data = AppUserSerializer(obj).data

        # Добавляю профиль в ответ, чтобы фронтенд мог сразу знать ID и тип профиля
        # Использую try/except - чтобы не ловить DoesNotExist, если по какой-то причине профиль не создался
        try:
            if obj.role.role.lower() == "psychologist":
                profile = PsychologistProfile.objects.get(user=obj)
                data["profile"] = PsychologistProfileSerializer(profile).data
            elif obj.role.role.lower() == "client":
                profile = ClientProfile.objects.get(user=obj)
                data["profile"] = ClientProfileSerializer(profile).data
        except (PsychologistProfile.DoesNotExist, ClientProfile.DoesNotExist):
            data["profile"] = None

        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Кастомный класс-сериализатор JWT-токенов, позволяющий вход по email.
    Используется вместо стандартного TokenObtainPairSerializer из SimpleJWT (потому что вход по enail)."""

    # ВАЖНО! Необходимо указать, что username_field - это будет email.
    # До этого мы указывали в модели это "USERNAME_FIELD = "email"" но это настройка Django, например, в админке,
    # логике логина, командах createsuperuser и т.п. Но это не влияет на процессы DRF. Соответственно, логика
    # сериализатора от DRF Simple JWT не смотрит на USERNAME_FIELD модели автоматически. Поэтому чтобы Simple JWT
    # понял, что логин должен быть по email, а не по username, нужно явно указать это в сериализаторе в username_field
    username_field = AppUser.EMAIL_FIELD

    def validate(self, attrs):
        """Валидация данных при получении JWT-токенов для пользователя по email (проверка пользователя и пароля).
        Возвращает стандартные токены SimpleJWT + дополнительную информацию о пользователе (UUID, email, роль)."""

        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise AuthenticationFailed("Необходимо указать email и пароль.")

        try:
            user = AppUser.objects.get(email=email)
        except AppUser.DoesNotExist:
            raise AuthenticationFailed("Пользователь с таким email не найден.")

        if not user.is_active:
            raise AuthenticationFailed("Аккаунт деактивирован. Обратитесь в поддержку.")

        if not user.check_password(password):
            raise AuthenticationFailed("Неверный пароль.")

        # Если все ок, то формирую словарь, чтобы передать в родительский "validate()"
        data = super().validate(
            {
                self.username_field: user.email,  # Ключ "email", значение - email пользователя
                "password": password,
            }
        )
        # Добавляю еще полезные данные в ответ (опционально, это полезно для будущего функционала)
        data.update({
            "user_uuid": str(user.uuid),  # UUID в JSON лучше передавать как строку
            "email": user.email,
            "role": user.role.role if user.role else None,
        })

        return data
