from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from users.constants import GENDER_CHOICES
from users.mixins.creator_mixin import CreatorMixin
from users.models import (AppUser, ClientProfile, Education, Method,
                          PsychologistProfile, Specialisation, Topic)
from users.services.send_verification_email import send_verification_email


class TopicSerializer(CreatorMixin, serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе модели Topic. Описывает, какие поля из Topic будут участвовать в сериализации/десериализации."""

    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Topic
        fields = ["id", "creator", "type", "group_name", "name", "slug", "created_at", "updated_at"]
        read_only_fields = ["id", "creator", "created_at", "updated_at"]


class SpecialisationSerializer(CreatorMixin, serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе Specialisation. Описывает, какие поля из Specialisation будут участвовать в сериализации/десериализации."""

    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Specialisation
        fields = ["id", "creator", "name", "description", "slug", "created_at", "updated_at"]
        read_only_fields = ["id", "creator", "created_at", "updated_at"]


class MethodSerializer(CreatorMixin, serializers.ModelSerializer):
    """Класс-сериализатор с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе модели Method. Описывает, какие поля из Method будут участвовать в сериализации/десериализации."""

    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Method
        fields = ["id", "creator", "name", "description", "slug", "created_at", "updated_at"]
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
            "created_at",
            "updated_at",
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

    # SlugRelatedField(read_only=True) не создает и не меняет ничего, а просто берет существующее значение
    # поля role из связанного объекта UserRole, чтоб вывести роль в ответе как человекочитаемую строку.
    role = serializers.SlugRelatedField(read_only=True, slug_field="role")

    class Meta:
        model = AppUser
        # Лучше не использовать fields = "__all__" потому что с "__all__" наш API отдаст все поля,
        # включая is_staff, is_superuser и т.п. Это опасно, потому что через API можно будет
        # назначить себе суперправа.
        fields = [
            "uuid",
            "email",
            "first_name",
            "last_name",
            "age",
            "phone_number",
            "role",
            "timezone",
            "password",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uuid", "role", "is_staff", "is_superuser", "is_active", "last_login", "created_at", "updated_at"
        ]
        # extra_kwargs - это зарезервированное имя в Meta-классе ModelSerializer для настройки конкретных полей,
        # например, ниже указываю что пароль только на ЗАПИСЬ. Т.е., его можно отправить через POST/PUT/PATCH,
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


class PsychologistProfileReadSerializer(serializers.ModelSerializer):
    """Read-сериализатор (используется для GET - создавать/редактировать вложенные объекты через него нельзя)
    с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе модели PsychologistProfile. Описывает, какие поля из PsychologistProfile будут участвовать в
    сериализации/десериализации."""

    specialisations = SpecialisationSerializer(read_only=True, many=True)
    methods = MethodSerializer(read_only=True, many=True)
    topics = TopicSerializer(read_only=True, many=True)
    educations = serializers.SerializerMethodField()  # забираем записи из модели Education по creator (AppUser)

    class Meta:
        model = PsychologistProfile
        fields = [
            "id",
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
            "is_verified",
            "is_all_education_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "is_verified", "is_all_education_verified", "rating", "created_at", "updated_at"
        ]

    def get_educations(self, obj):
        """Получаем из модели Education записи текущего психолога."""
        user = obj.user
        return EducationSerializer(
            Education.objects.filter(creator=user).order_by("-year_start"),
            many=True
        ).data


class PsychologistProfileWriteSerializer(serializers.ModelSerializer):
    """Write-сериализатор (используется для PATCH/PUT - разрешает модифицировать только связи через список PK)
    с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе модели PsychologistProfile. Описывает, какие поля из PsychologistProfile будут участвовать в
    сериализации/десериализации."""

    specialisations = serializers.PrimaryKeyRelatedField(
        queryset=Specialisation.objects.all(),
        many=True,
        required=False
    )
    methods = serializers.PrimaryKeyRelatedField(
        queryset=Method.objects.all(),
        many=True,
        required=False
    )
    topics = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = PsychologistProfile
        fields = [
            "gender",
            "specialisations",
            "methods",
            "topics",
            "biography",
            "photo",
            "work_experience",
            "languages",
            "therapy_format",
            "price_individual",
            "price_couples",
            "work_status",
        ]

    def update(self, instance, validated_data):
        """Метод для обновления M2M через set(), а остальные поля через super()."""

        m2m_fields = ["specialisations", "methods", "topics"]

        # Обрабатываем M2M поля
        for field in m2m_fields:
            if field in validated_data:
                values = validated_data.pop(field)
                getattr(instance, field).set(values)

        # Обновляем обычные поля
        return super().update(instance, validated_data)


class ClientProfileReadSerializer(serializers.ModelSerializer):
    """Read-сериализатор (используется для GET - создавать/редактировать вложенные объекты через него нельзя)
     с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе ClientProfile. Описывает, какие поля из ClientProfile будут участвовать в сериализации/десериализации."""

    preferred_methods = MethodSerializer(read_only=True, many=True)
    requested_topics = TopicSerializer(read_only=True, many=True)

    class Meta:
        model = ClientProfile
        fields = ["id", "therapy_experience", "preferred_methods", "requested_topics", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClientProfileWriteSerializer(serializers.ModelSerializer):
    """Write-сериализатор (используется для PATCH/PUT - разрешает модифицировать только связи через список PK)
     с использованием класса ModelSerializer для осуществления базовой сериализация в DRF на
    основе ClientProfile. Описывает, какие поля из ClientProfile будут участвовать в сериализации/десериализации."""

    preferred_methods = serializers.PrimaryKeyRelatedField(
        queryset=Method.objects.all(),
        many=True,
        required=False
    )
    requested_topics = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = ClientProfile
        fields = ["therapy_experience", "preferred_methods", "requested_topics"]

    def update(self, instance, validated_data):
        """Метод для обновления M2M через set(), а остальные поля через super()."""

        m2m_fields = ["preferred_methods", "requested_topics"]

        # Обрабатываем M2M поля
        for field in m2m_fields:
            if field in validated_data:
                values = validated_data.pop(field)
                getattr(instance, field).set(values)

        # Обновляем обычные поля
        return super().update(instance, validated_data)


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор-"оркестр" (он соединяет разные сериализаторы) для регистрации нового пользователя в системе.
    В зависимости от выбранной роли создает связанный профиль: PsychologistProfile или ClientProfile."""

    # Для всех профилей:
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    gender = serializers.ChoiceField(choices=GENDER_CHOICES, required=False, allow_null=True)

    # Доп для профиля психолога:
    specialisations = serializers.PrimaryKeyRelatedField(
        queryset=Specialisation.objects.all(), many=True, required=False
    )
    methods = serializers.PrimaryKeyRelatedField(
        queryset=Method.objects.all(), many=True, required=False
    )
    topics = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(), many=True, required=False
    )

    # Доп для профиля клиента:
    preferred_methods = serializers.PrimaryKeyRelatedField(
        queryset=Method.objects.all(), many=True, required=False
    )
    requested_topics = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(), many=True, required=False
    )

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
            "specialisations",
            "methods",
            "topics",
            "preferred_methods",
            "requested_topics",
        ]
        read_only_fields = ["role",]
        # Важно отключить в сериализаторе DRF UniqueValidator для поля email (unique=True).
        # Иначе DRF перехватит ошибку первым из модели (unique=True) и метод validate_email() не сработает
        # при проверке наличия пользователя с таким email, но без подтверждения регистрации.
        extra_kwargs: dict = {
            "email": {"validators": []}
        }

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

    def validate_email(self, value):
        """Метод для проверки наличия пользователя с уже существующим email в БД.
            1) У нас в модели указано unique=True и лучше это проверять в сериализаторе заранее, чтоб не
            получать потом IntegrityError на уровне БД при регистрации.
            2) Можно добавить в validate(), а можно так и через отдельный validate_email().
        Когда email уже есть:
        - если активный пользователь - то ошибка.
        - если НЕ активный - то разрешаем, но помечаем, что надо отправить письмо подтверждение активации повторно."""
        user = AppUser.objects.filter(email=value).first()

        if user:
            # Если is_active=True
            if user.is_active:
                raise serializers.ValidationError("Пользователь с таким email уже зарегистрирован.")

            # А если is_active=False, то помечаю в контекст сериализатора, что это повторная регистрация без ошибок
            self.context["existing_inactive_user"] = user

        return value

    # @transaction.atomic - это декоратор, который оборачивает блок кода в одну транзакцию базы данных.
    # Т.е., если внутри create() произойдет любая ошибка (например, не удалось создать профиль), то:
    # 1) Django откатит все изменения;
    # 2) И в базе не останется "половинчатых" данных (например, пользователь без профиля).
    @transaction.atomic
    def create(self, validated_data):
        """Метод для создания пользователя и автоматического профиля для него в зависимости от роли."""
        # Проверяю, есть ли пользователь, для которого требуется resend письма с подтверждением/активацией
        existing_user = self.context.get("existing_inactive_user")

        if existing_user:
            # Только повторная отправка письма без каких-либо обновлений пароля, профиля и т.д.
            send_verification_email(existing_user)
            # А также фиксирую в контексте новый флаг, что это существующий пользователь без подтверждения регистрации
            self.context["inactive_user_resend"] = True

            return existing_user

        password = validated_data.pop("password")
        gender = validated_data.pop("gender", "")
        role = self.context.get("role")
        specialisations = validated_data.pop("specialisations", [])
        methods = validated_data.pop("methods", [])
        topics = validated_data.pop("topics", [])
        preferred_methods = validated_data.pop("preferred_methods", [])
        requested_topics = validated_data.pop("requested_topics", [])

        # Создание пользователя
        user = AppUser(**validated_data, role=role)
        user.set_password(password)
        user.save()
        send_verification_email(user)  # Отправка email с подтверждением регистрации для изменения is_active на True

        # И сразу автоматическое создание профиля для данного пользователя:
        match role.role.strip().lower():
            case "psychologist":
                ps_profile = PsychologistProfile.objects.create(user=user, gender=gender)
                ps_profile.specialisations.set(specialisations)
                ps_profile.methods.set(methods)
                ps_profile.topics.set(topics)
            case "client":
                cl_profile = ClientProfile.objects.create(user=user)
                cl_profile.preferred_methods.set(preferred_methods)
                cl_profile.requested_topics.set(requested_topics)

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
    Используется вместо стандартного TokenObtainPairSerializer из SimpleJWT (потому что вход по email)."""

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


class LogoutSerializer(serializers.Serializer):
    """Кастомный класс-сериализатор для логаута. Принимает refresh токен и заносит его в blacklist."""

    refresh = serializers.CharField()

    def validate(self, attrs):
        """Метод для валидации входных данных. Этот метод просто извлекает refresh-токен из запроса и сохраняет
        его в self.token - это нужно, чтобы потом метод save() мог вызвать blacklist() для этого токена.
        Возвращает словарь attrs без изменений."""
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs):
        """Метод для занесения указанного refresh-токен в blacklist."""
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError:
            raise serializers.ValidationError({"refresh": "Токен невалидный или истек срок действия."})


class ChangePasswordSerializer(serializers.Serializer):
    """Кастомный класс-сериализатор для изменения пароля авторизованным пользователем."""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        """Метод для проверки корректности введенного старого пароля."""
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")

        return value

    def validate(self, attrs):
        """Метод для проверки совпадения паролей."""
        new_password = attrs.get("new_password")
        new_password_confirm = attrs.get("new_password_confirm")

        if new_password != new_password_confirm:
            raise serializers.ValidationError({"new_password_confirm": "Пароли не совпадают."})

        # validate_password() - это стандартная проверка Django validators (min_length, CommonPasswordValidator и т.д.)
        validate_password(new_password)

        return attrs

    def save(self, **kwargs):
        """Метод для сохранения нового пароля."""
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()

        return user


class PasswordResetSerializer(serializers.Serializer):
    """Кастомный класс-сериализатор для запроса на сброс пароля (ввод email)."""

    email = serializers.EmailField()

    def validate_email(self, value):
        """Метод для проверки наличия пользователя с уже существующим email в БД.
        Не выдаем ошибку, если пользователя нет. Просто возвращаемся дальше (против утечки данных, что такой
        пользователь есть у нас в БД)."""
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Кастомный класс-сериализатор для подтверждения сброса пароля"""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(required=True, write_only=True)
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        """Метод для валидации данных:
        1) Проверяет совпадение паролей.
        2) Проверяет uid.
        3) Проверяет token."""
        new_password = attrs.get("new_password")
        new_password_confirm = attrs.get("new_password_confirm")

        if new_password != new_password_confirm:
            raise serializers.ValidationError({"new_password_confirm": "Пароли не совпадают."})

        # Раскодируем uid и ищем пользователя
        uidb64 = attrs.get("uid")

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
        except Exception:
            raise serializers.ValidationError({"uid": "Некорректный uid."})

        try:
            user = AppUser.objects.get(pk=uid)
        except AppUser.DoesNotExist:
            raise serializers.ValidationError({"uid": "Пользователь не найден."})

        # Сохраняю пользователя в контексте для save()
        attrs["user_obj"] = user

        # Проверяю токен
        token = attrs.get("token")

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({"token": "Недействительный или просроченный токен."})

        # validate_password() - это стандартная проверка Django validators (min_length, CommonPasswordValidator и т.д.)
        validate_password(new_password)

        return attrs

    def save(self, **kwargs):
        """Метод для сохранения нового пароля у пользователя."""
        user = self.validated_data["user_obj"]
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save()

        return user
