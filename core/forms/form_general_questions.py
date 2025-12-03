from django import forms
from django.db import transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from timezone_field import TimeZoneFormField


class ClientGeneralQuestionsForm(forms.Form):
    """Кастомная форма для страницы *Общие вопросы*. Форма объединяет данные из двух моделей: AppUser и ClientProfile.
    Основная логика:
        - При GET форма получает initial-значения из связанных моделей, чтобы пользователь сразу видел
         уже заполненные данные.
        - При POST форма валидирует и сохраняет обновленные данные.
        - Email здесь отображается только для чтения (нельзя изменить), так как изменение email реализуем
        отдельно в *Мой профиль*."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        help_text="Введите имя",
    )
    email = forms.EmailField(
        required=False,
        disabled=True,  # поле только для чтения
        help_text="Email отображается только для чтения",
    )
    age = forms.IntegerField(
        required=True,
        help_text="Введите возраст",
        validators=[MinValueValidator(18), MaxValueValidator(120)],
    )
    timezone = TimeZoneFormField(
        required=True,
        help_text="Для корректного отображения расписаний сессий",
    )
    therapy_experience = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Был ли у вас опыт терапии?",
    )

    def save(self, user):
        """Сохранение данных формы в модели AppUser и ClientProfile.
        Логика:
            1) Обновляем поля пользователя: first_name, age, timezone (email - только для чтения и НЕ обновляется).
            2) Обновляем client_profile.therapy_experience.
            3) Используем транзакцию, чтобы гарантировать целостность данных."""

        cleaned_data = self.cleaned_data

        with transaction.atomic():

            user.first_name = cleaned_data["first_name"]
            user.age = cleaned_data["age"]
            user.timezone = cleaned_data["timezone"]
            user.save()

            profile = user.client_profile
            profile.therapy_experience = cleaned_data["therapy_experience"]
            profile.save()

        return user

    # def clean_email(self):
    #     """Метод для валидации введенного email:
    #         - если клиент вводит свой же email или email, которого нет в БД, то это ок
    #         - если вводит email другого уже существующего пользователя, то выводим ошибку."""
    #     if AppUser.objects.exclude(pk=request.user.pk).filter(email=email).exists():
    #         raise ValidationError(
    #             "Этот email уже используется другим пользователем."
    #         )
