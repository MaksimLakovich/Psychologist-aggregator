import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.core.validators import MinValueValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from slugify import slugify
from timezone_field import TimeZoneField

from users.managers import AppUserManager


class TimeStampedModel(models.Model):
    """Абстрактная базовая модель для дальнейшего создания *created_at* и *updated_at*
    во всех моделях приложения при необходимости."""

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания:",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления:",
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
        verbose_name="Создатель:",
        help_text="Укажите пользователя, создавшего запись",
    )
    role = models.CharField(
        unique=True,
        max_length=50,
        null=False,
        blank=False,
        verbose_name="Роль пользователя:",
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
        verbose_name="Создатель:",
        help_text="Укажите пользователя, создавшего запись",
    )
    type = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        verbose_name="Вид запроса:",
        help_text="Укажите вид запроса",
    )
    name = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Название запроса:",
        help_text="Укажите название запроса",
    )
    slug = models.SlugField(
        unique=True,
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Slug-название запроса:",
        help_text="Укажите slug-название запроса",
    )

    def save(self, *args, **kwargs):
        """Если slug не указан, то метод сгенерирует его автоматически из name."""
        if not self.slug:
            # Установка "poetry add python-slugify" и импорт "from slugify import slugify"
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.type}: '{self.name}'"

    class Meta:
        verbose_name = "Тема"
        verbose_name_plural = "Темы"
        ordering = ["type", "name"]
        unique_together = ("type", "name")


class Specialisation(TimeStampedModel):
    """Модель представляет специализацию (методологическая школа) - то в чем психолог специализируется."""
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_specialisations",
        verbose_name="Создатель:",
        help_text="Укажите пользователя, создавшего запись",
    )
    name = models.CharField(
        unique=True,
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Название специализации:",
        help_text="Укажите название специализации",
    )
    description = models.TextField(
        null=False,
        blank=False,
        verbose_name="Описание специализации:",
        help_text="Укажите описание специализации",
    )
    slug = models.SlugField(
        unique=True,
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Slug-название специализации:",
        help_text="Укажите slug-название специализации",
    )

    def save(self, *args, **kwargs):
        """Если slug не указан, то метод сгенерирует его автоматически из name."""
        if not self.slug:
            # Установка "poetry add python-slugify" и импорт "from slugify import slugify"
            self.slug = slugify(self.name)
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
        verbose_name="Создатель:",
        help_text="Укажите пользователя, создавшего запись",
    )
    name = models.CharField(
        unique=True,
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Название метода:",
        help_text="Укажите название метода",
    )
    description = models.TextField(
        null=False,
        blank=False,
        verbose_name="Описание метода:",
        help_text="Укажите описание метода",
    )
    slug = models.SlugField(
        unique=True,
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Slug-название метода:",
        help_text="Укажите slug-название метода",
    )

    def save(self, *args, **kwargs):
        """Если slug не указан, то метод сгенерирует его автоматически из name."""
        if not self.slug:
            # Установка "poetry add python-slugify" и импорт "from slugify import slugify"
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.name}"

    class Meta:
        verbose_name = "Метод"
        verbose_name_plural = "Методы"
        ordering = ["name",]


class AppUser(AbstractBaseUser, TimeStampedModel):
    """Модель представляет пользователя приложения."""

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
        verbose_name="Имя:",
        help_text="Введите имя",
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Фамилия:",
        help_text="Введите фамилию",
    )
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(18)],
        blank=False,
        null=False,
        verbose_name="Возраст:",
        help_text="Введите возраст",
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Email:",
        help_text="Введите email",
    )
    # Установка "poetry add django-phonenumber-field" и "poetry add phonenumbers" + импорт
    # "from phonenumber_field.modelfields import PhoneNumberField" + INSTALLED_APPS + PHONENUMBER_DEFAULT_REGION
    phone_number = PhoneNumberField(
        blank=True,
        null=True,
        verbose_name="Телефон:",
        help_text="Введите номер телефона",
    )
    role = models.ForeignKey(
        to="users.UserRole",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Роль пользователя:",
        help_text="Укажите роль пользователя",
    )
    # Установка "poetry add django-timezone-field"
    # + импорт "from timezone_field import TimeZoneField" + INSTALLED_APPS
    timezone = TimeZoneField(
        blank=True,
        null=True,
        verbose_name="Часовой пояс:",
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
    is_superuser = models.BooleanField(
        default=False,
        verbose_name="Суперпользователь?",
        help_text="Доступ суперпользователя"
    )

    objects = AppUserManager()  # Указываю кастомный менеджер для пользователя без поля username

    # Определяет, какое поле будет использоваться в качестве уникального идентификатора для аутентификации юзера
    USERNAME_FIELD = "email"
    # Обязательные поля, которые должны быть указаны при создании суперпользователя через команду createsuperuser
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        """Метод определяет строковое представление объекта. Полезно для отображения объектов в админке/консоли."""
        return f"{self.email}"

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["email"]
        db_table = "users"


# - `Education`: **country**, **institution**, **degree**, **specialisation**, **year_start**, **year_end**,
# **document_url**, **verified** (bool)
#
# - `PsychologistProfile`:
#   - расширяется полями модели `AppUser`
#   - **is_verified** (флаг модерации администратором), **gander**, **bio**, **photo**, **work_experience_years**,
#   **education_verified** (bool), **therapy_format** (например, "online", "встреча", "любой"), **price**,
#   **status** (например, "работает", "не работает")
#   - **specialisations** (один ко многим, связь с моделью `Specialisation`)
#   - **methods** (один ко многим, связь с моделью `Method`)
#   - **topics** (один ко многим, связь с моделью `Topic`)
#   - **educations** (один ко многим, связь с моделью `Education`)
#   - **languages** (default="русский", потом можно расширить и добавить доп. фильтрацию)
#   - **rating** (default=null, функционал 2-го этапа)
#
# - `ClientProfile`:
#   - расширяется полями модели `AppUser` (исключения: last_name, is_active, is_staff, is_superuser)
#   - **therapy_experience**
#   - **methods** (один ко многим, связь с моделью `Method`)
#   - **topics** (один ко многим, связь с моделью `Topic`)
