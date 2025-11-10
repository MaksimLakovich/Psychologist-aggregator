import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import (FileExtensionValidator, MaxValueValidator,
                                    MinValueValidator)
from django.db import models
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from timezone_field import TimeZoneField

from users.constants import (GENDER_CHOICES, LANGUAGE_CHOICES,
                             THERAPY_FORMAT_CHOICES, WORK_STATUS_CHOICES)
from users.managers import AppUserManager
from users.services.defaults import default_languages
from users.services.slug import generate_unique_slug
from users.validators import validate_file_size


class TimeStampedModel(models.Model):
    """Абстрактная базовая модель для дальнейшего создания *created_at* и *updated_at*
    во всех моделях приложения при необходимости."""

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    class Meta:
        """Обязательный параметр для абстрактных базовых моделей."""
        abstract = True


class UserRole(TimeStampedModel):
    """Модель представляет роли пользователей в приложении."""
    # Использую строку в to="users.AppUser" (рекомендуется для ForeignKey к User) вместо to=AppUser, чтоб
    # избежать ошибки циклического импорта (circular import), которая может возникнуть
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_roles",
        verbose_name="Создатель",
        help_text="Укажите пользователя, создавшего запись",
    )
    role = models.CharField(
        unique=True,
        max_length=50,
        null=False,
        blank=False,
        verbose_name="Роль пользователя",
        help_text="Укажите роль пользователя",
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.role}"

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        ordering = ["role",]


class Topic(TimeStampedModel):
    """Модель представляет тему/вопрос (запрос на терапию) - то с чем клиент приходит."""
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_topics",
        verbose_name="Создатель",
        help_text="Укажите пользователя, создавшего запись",
    )
    type = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        verbose_name="Вид запроса",
        help_text="Укажите вид запроса",
    )
    group_name = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        verbose_name="Группа запросов",
        help_text="Укажите название группы запроса",
    )
    name = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Название запроса",
        help_text="Укажите название запроса",
    )
    slug = models.SlugField(
        unique=True,
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Slug-название запроса",
        help_text="Укажите slug-название запроса",
    )

    def save(self, *args, **kwargs):
        """Если slug не указан, то метод сгенерирует его автоматически из name."""
        if not self.slug:
            # Установка "poetry add python-slugify" и импорт "from slugify import slugify"
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.type}: '{self.name}'"

    class Meta:
        verbose_name = "Тема"
        verbose_name_plural = "Темы"
        ordering = ["type", "name"]
        unique_together = ("type", "group_name", "name")


class Specialisation(TimeStampedModel):
    """Модель представляет специализацию (методологическая школа) - то в чем психолог специализируется."""
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_specialisations",
        verbose_name="Создатель",
        help_text="Укажите пользователя, создавшего запись",
    )
    name = models.CharField(
        unique=True,
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Название специализации",
        help_text="Укажите название специализации",
    )
    description = models.TextField(
        null=False,
        blank=False,
        verbose_name="Описание специализации",
        help_text="Укажите описание специализации",
    )
    slug = models.SlugField(
        unique=True,
        max_length=255,
        blank=True,
        verbose_name="Slug-название специализации",
        help_text="Укажите slug-название специализации",
    )

    def save(self, *args, **kwargs):
        """Если slug не указан, то метод сгенерирует его автоматически из name."""
        if not self.slug:
            # Установка "poetry add python-slugify" и импорт "from slugify import slugify"
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.name}"

    class Meta:
        verbose_name = "Специализация"
        verbose_name_plural = "Специализации"
        ordering = ["name",]


class Method(TimeStampedModel):
    """Модель представляет метод (инструмент/подход), который использует психолог в работе."""
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_methods",
        verbose_name="Создатель",
        help_text="Укажите пользователя, создавшего запись",
    )
    name = models.CharField(
        unique=True,
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Название метода",
        help_text="Укажите название метода",
    )
    description = models.TextField(
        null=False,
        blank=False,
        verbose_name="Описание метода",
        help_text="Укажите описание метода",
    )
    slug = models.SlugField(
        unique=True,
        max_length=255,
        blank=True,
        verbose_name="Slug-название метода",
        help_text="Укажите slug-название метода",
    )

    def save(self, *args, **kwargs):
        """Если slug не указан, то метод сгенерирует его автоматически из name."""
        if not self.slug:
            # Установка "poetry add python-slugify" и импорт "from slugify import slugify"
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.name}"

    class Meta:
        verbose_name = "Метод"
        verbose_name_plural = "Методы"
        ordering = ["name",]


class Education(TimeStampedModel):
    """Модель представляет образование, которое есть у психолога."""
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="created_educations",
        verbose_name="Создатель",
        help_text="Укажите пользователя, создавшего запись",
    )
    # Для вывода списка стран использую django_countries (poetry add django-countries)
    country = CountryField(
        verbose_name="Страна",
        null=False,
        blank=False,
        help_text="Выберите страну учебного заведения",
    )
    institution = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Учебное учреждение",
        help_text="Укажите название учебного учреждения",
    )
    degree = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Ученая степень / квалификация",
        help_text="Например: Бакалавр, Магистр, Специалист, Сертификат",
    )
    specialisation = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Специализация / направление",
        help_text="Специализация или программа обучения",
    )
    # Храним только год - чаще всего это то, что нужно. Диапазон: от 1900 до 2100
    year_start = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(2100)],
        null=False,
        blank=False,
        verbose_name="Год начала обучения",
        help_text="Укажите год начала обучения",
    )
    year_end = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(2100)],
        null=True,
        blank=True,
        verbose_name="Год окончания обучения",
        help_text="Укажите год окончания обучения или оставьте пустым, если обучение в процессе",
    )
    document = models.FileField(
        upload_to="education_docs/%Y/%m/%d",
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"]), validate_file_size],
        null=True,
        blank=True,
        verbose_name="Скан диплома/сертификата",
        help_text="Прикрепите скан диплома/сертификата",
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Верификация",
        help_text="Флаг модерации подлинности (проверяется администратором)",
    )

    def clean(self):
        """Дополнительная логическая валидация полей - убедиться, что year_start <= year_end (если year_end указан)."""
        super().clean()
        if self.year_end is not None and self.year_end < self.year_start:
            raise ValidationError(
                {"year_end": "Год окончания не может быть раньше года начала."}
            )
        if self.year_start < 1900:
            raise ValidationError(
                {"year_start": "Некорректный год начала обучения."}
            )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.country} / {self.institution} / {self.specialisation}"

    class Meta:
        verbose_name = "Образование"
        verbose_name_plural = "Образования"
        ordering = ["country", "institution", "specialisation"]


class AppUser(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Модель представляет пользователя приложения."""

    username = None  # type: ignore
    # Это как primary_key вместо системного автоинкремента id, чтоб было более безопасно для публичных API
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    first_name = models.CharField(
        max_length=150,
        blank=False,
        null=False,
        verbose_name="Имя",
        help_text="Введите имя",
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Фамилия",
        help_text="Введите фамилию",
    )
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(18), MaxValueValidator(120)],
        null=False,
        blank=False,
        verbose_name="Возраст",
        help_text="Введите возраст",
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Введите email",
    )
    # Установка "poetry add django-phonenumber-field" и "poetry add phonenumbers" + импорт
    # "from phonenumber_field.modelfields import PhoneNumberField" + INSTALLED_APPS + PHONENUMBER_DEFAULT_REGION
    phone_number = PhoneNumberField(
        blank=True,
        null=False,
        verbose_name="Телефон",
        help_text="Введите номер телефона",
    )
    role = models.ForeignKey(
        to="users.UserRole",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Роль пользователя",
        help_text="Укажите роль пользователя",
    )
    # Установка "poetry add django-timezone-field"
    # + импорт "from timezone_field import TimeZoneField" + INSTALLED_APPS
    timezone = TimeZoneField(
        blank=True,
        null=True,
        verbose_name="Часовой пояс",
        help_text="Для корректного отображения расписаний сессий",
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Персонал?",
        help_text="Административный доступ"
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name="Активный?",
        help_text="Аккаунт активен"
    )

    objects = AppUserManager()  # Указываю кастомный менеджер для пользователя без поля username

    # Определяет, какое поле будет использоваться в качестве уникального идентификатора для аутентификации юзера
    USERNAME_FIELD = "email"
    # Обязательные поля, которые должны быть указаны при создании суперпользователя через команду createsuperuser
    REQUIRED_FIELDS = ["first_name", "last_name"]
    # Это нужно для корректно работы сериализатора для авторизации с токеном из-за того, что мы используем email
    # вместо username
    EMAIL_FIELD = "email"

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.email}"

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["email"]


class PsychologistProfile(TimeStampedModel):
    """Модель представляет профиль психолога."""

    user = models.OneToOneField(
        to=AppUser,
        on_delete=models.CASCADE,
        related_name="psychologist_profile",
        verbose_name="Пользователь",
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Верификация пользователя",
        help_text="Флаг модерации подлинности (проверяется администратором)",
    )
    gender = models.CharField(
        choices=GENDER_CHOICES,
        null=False,
        blank=False,
        verbose_name="Пол",
        help_text="Укажите пол",
    )
    # specialisations: "Когнитивно-поведенческая терапия", "Психоанализ", "Гештальт-терапия", "Семейная терапия" и т.д.
    specialisations = models.ManyToManyField(
        to=Specialisation,
        blank=True,
        related_name="specialisation_psychologists",
        verbose_name="Специализация",
        help_text="Добавьте специализацию (методологическая школа)",
    )
    # methods: "Схематерапия", "НЛП" и т.д.
    methods = models.ManyToManyField(
        to=Method,
        blank=True,
        related_name="method_psychologists",
        verbose_name="Метод",
        help_text="Добавьте методы (инструмент/подход)",
    )
    # topics: "Развод", "Выгорание", "Панические атаки", "Тревожность" и т.д.
    topics = models.ManyToManyField(
        to=Topic,
        blank=True,
        related_name="topic_psychologists",
        verbose_name="Запрос",
        help_text="Добавьте тему/вопрос (запрос на терапию)",
    )
    educations = models.ManyToManyField(
        to=Education,
        blank=True,
        related_name="education_psychologists",
        verbose_name="Образование",
        help_text="Добавьте образование",
    )
    is_all_education_verified = models.BooleanField(
        default=False,
        verbose_name="Верификация образования",
        help_text="Флаг модерации подлинности (проверяется администратором)",
    )
    biography = models.TextField(
        null=True,
        blank=True,
        verbose_name="О специалисте",
        help_text="Добавьте информацию о себе",
    )
    photo = models.ImageField(
        upload_to="photo/%Y/%m/%d",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"]), validate_file_size],
        null=True,
        blank=True,
        verbose_name="Фотография профиля",
        help_text="Добавьте фотографию вашего профиля",
    )
    work_experience = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
        verbose_name="Опыт",
        help_text="Укажите текущий опыт работы (лет)",
    )
    languages = ArrayField(
        models.CharField(max_length=50, choices=LANGUAGE_CHOICES),
        default=default_languages,
        verbose_name="Языки",
        help_text="Укажите языки, на которых можно проводить сессии",
    )
    therapy_format = models.CharField(
        choices=THERAPY_FORMAT_CHOICES,
        default="online",
        blank=False,
        verbose_name="Формат сессии",
        help_text="Укажите возможны формат для проведения сессий",
    )
    price_individual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        blank=False,
        verbose_name="Стоимость индивидуальной сессии (руб.)",
        help_text="Укажите стоимость индивидуальной сессии (руб.)",
    )
    price_couples = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        blank=False,
        verbose_name="Стоимость парной сессии (руб.)",
        help_text="Укажите стоимость парной сессии (руб.)",
    )
    work_status = models.CharField(
        choices=WORK_STATUS_CHOICES,
        default="working",
        blank=False,
        verbose_name="Рабочий статус",
        help_text="Текущий рабочий статус психолога",
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0.0,
        blank=False,
        verbose_name="Рейтинг",
        help_text="Рейтинг психолога",
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.user.email}"

    class Meta:
        verbose_name = "Психолог"
        verbose_name_plural = "Психологи"
        ordering = ["user__email"]


class ClientProfile(TimeStampedModel):
    """Модель представляет профиль клиента."""

    user = models.OneToOneField(
        to=AppUser,
        on_delete=models.CASCADE,
        related_name="client_profile",
        verbose_name="Пользователь",
    )
    therapy_experience = models.BooleanField(
        default=False,
        verbose_name="Опыт терапии",
        help_text="Был ли у вас опыт терапии?",
    )
    # methods: "Схематерапия", "НЛП" и т.д.
    preferred_methods = models.ManyToManyField(
        to=Method,
        blank=True,
        related_name="method_clients",
        verbose_name="Предпочтительные методы",
        help_text="Методы или подходы, которые вам близки",
    )
    # topics: "Развод", "Выгорание", "Панические атаки", "Тревожность" и т.д.
    requested_topics = models.ManyToManyField(
        to=Topic,
        blank=True,
        related_name="topic_clients",
        verbose_name="Запросы",
        help_text="Темы, с которыми вы хотите работать",
    )

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.user.email}"

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ["user__email"]
