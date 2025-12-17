from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import (AppUser, ClientProfile, Education, Method,
                          PsychologistProfile, Specialisation, Topic, UserRole)


class CreatorAndReadonlyFields(admin.ModelAdmin):
    """Базовый класс для админок, чтоб не дублировать в них повторяющийся код
    (например, параметры для readonly_fields или функцию сохранения creator при создании объекта."""

    readonly_fields = ("creator", "created_at", "updated_at")  # чтобы в админке их случайно не изменили

    def save_model(self, request, obj, form, change):
        """Автоматическое сохранение creator в создаваемом объекте."""
        if not obj.creator_id:
            obj.creator = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserRole)
class UserRoleAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели UserRole в админке."""

    list_display = ("id", "creator", "role")
    search_fields = ("role",)
    ordering = ("role",)
    list_display_links = ("role",)  # чтобы кликать на имя роли вместо ID


@admin.register(Topic)
class TopicAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели Topic в админке."""

    list_display = ("id", "creator", "type", "group_name", "name", "slug")
    list_filter = ("type", "group_name")
    search_fields = ("type", "group_name", "name", "slug")
    ordering = ("type", "group_name", "name")
    list_display_links = ("name",)  # чтобы кликать на название вместо ID
    prepopulated_fields = {"slug": ("name",)}  # чтобы slug создавался автоматически при вводе имени


@admin.register(Specialisation)
class SpecialisationAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели Specialisation в админке."""

    list_display = ("id", "creator", "name", "slug", "description")
    search_fields = ("name", "slug")
    ordering = ("name",)
    list_display_links = ("name",)  # чтобы кликать на название вместо ID
    prepopulated_fields = {"slug": ("name",)}  # чтобы slug создавался автоматически при вводе имени


@admin.register(Method)
class MethodAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели Method в админке."""

    list_display = ("id", "creator", "name", "slug", "description")
    search_fields = ("name", "slug")
    ordering = ("name",)
    list_display_links = ("name",)  # чтобы кликать на название вместо ID
    prepopulated_fields = {"slug": ("name",)}  # чтобы slug создавался автоматически при вводе имени


@admin.register(Education)
class EducationAdmin(CreatorAndReadonlyFields):
    """Настройка отображения модели Education в админке."""

    list_display = (
        "id", "creator", "country", "institution", "degree", "specialisation", "year_start", "year_end", "is_verified"
    )
    list_filter = ("institution", "degree", "specialisation")
    search_fields = ("country", "institution", "degree", "specialisation")
    ordering = ("country", "institution")
    # list_editable = ("is_verified",)  # чтоб поле было доступно для изменения прямо из списка без захода в продукт
    list_display_links = ("institution",)  # чтобы кликать на название вместо ID


@admin.register(AppUser)
class AppUserAdmin(UserAdmin):
    """Настройка отображения модели AppUser в админке."""

    model = AppUser

    list_display = (
        "uuid", "email", "first_name", "last_name", "role", "is_staff", "is_superuser", "is_active", "timezone"
    )
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    readonly_fields = ("uuid", "last_login", "created_at", "updated_at")  # чтобы в админке их случайно не изменили
    list_display_links = ("email",)  # чтобы открывать запись по email вместо ID

    # Группирует поля при редактировании пользователя:
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Персональная информация",
            {
                "fields": ("first_name", "last_name", "age", "phone_number", "timezone", "role")
            },
        ),
        (
            "Права доступа",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")
            },
        ),
        ("Даты", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    # Управляет полями при добавлении нового пользователя через админку
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "age",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "role",
                ),
            },
        ),
    )


@admin.register(PsychologistProfile)
class PsychologistProfileAdmin(admin.ModelAdmin):
    """Настройка отображения модели PsychologistProfile в админке."""

    list_display = (
        "id", "user", "is_verified", "is_all_education_verified", "practice_start_year", "therapy_format"
    )
    list_filter = ("specialisations", "methods", "topics", "therapy_format", "work_status")
    # # autocomplete_fields - улучшит производительность при большом объеме данных
    # autocomplete_fields = ("specialisations", "methods", "topics", "educations")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    ordering = ("user__email",)
    readonly_fields = ("user", "rating", "created_at", "updated_at")  # чтобы в админке их случайно не изменили


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    """Настройка отображения модели ClientProfile в админке."""

    list_display = ("id", "user", "therapy_experience", "has_preferences", "preferred_topic_type")
    list_filter = ("has_preferences", "preferred_topic_type", "preferred_methods", "therapy_experience")
    # # autocomplete_fields - улучшит производительность при большом объеме данных
    # autocomplete_fields = ("preferred_methods", "requested_topics")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    ordering = ("user__email",)
    readonly_fields = ("user", "created_at", "updated_at")  # чтобы в админке их случайно не изменили
