from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction
from timezone_field import TimeZoneFormField


class ClientGeneralQuestionsForm(forms.Form):
    """Кастомная форма для страницы *Общие вопросы*. Форма объединяет данные из двух моделей: AppUser и ClientProfile.
    Основная логика:
        - При GET форма получает initial-значения из связанных моделей, чтобы пользователь сразу видел
         уже заполненные данные (кроме timezone где мы изначально устанавливаем пусто).
        - При POST форма валидирует и сохраняет обновленные данные.
        - Email здесь отображается только для чтения (нельзя изменить), так как изменение email реализуем
        отдельно в *Мой профиль*."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "block w-full max-w-sm rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-lg "
                     "text-gray-900 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm",
            "placeholder": "Ваше имя",
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "readonly": "readonly",
            "class": "block w-full max-w-sm rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-lg "
                     "text-gray-900 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm cursor-not-allowed",
        })
    )
    age = forms.IntegerField(
        required=True,
        validators=[MinValueValidator(18), MaxValueValidator(120)],
        widget=forms.NumberInput(attrs={
            "class": "block w-full max-w-sm rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-lg "
                     "text-gray-900 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm",
            "placeholder": "Ваш возраст",
        })
    )
    therapy_experience = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "sr-only peer",
        })
    )
    timezone = TimeZoneFormField(
        required=True,
        # Чтоб на web-странице поле timezone не заполнялось по умолчанию первым initial-значением
        # из связанного справочника (было Africa/Abidjan)
        initial=None,
        widget=forms.Select(attrs={
            "class": "block w-full max-w-sm rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-lg "
                     "text-gray-900 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm",
        })
    )

    def __init__(self, *args, **kwargs):
        """Подготавливает форму под оба возможные сценарии шага "Общие вопросы":
            - сценарий 1: работает зарегистрированный авторизованный пользователь;
            - сценарий 2: работает guest-anonymous.

        init:
            1) добавляет в список timezone пустой первый пункт "Выберите часовой пояс", чтобы пользователь
              не получал случайно выбранный timezone по умолчанию и не переходил к подбору слота с некорректным TZ;
            2) переключает поле email между двумя сценариями:
               - сценарий 1: для авторизованного клиента email остается read-only;
               - сценарий 2: для гостя email становится обычным редактируемым полем, потому что он вводит его впервые.
        """
        email_readonly = kwargs.pop("email_readonly", True)
        super().__init__(*args, **kwargs)

        # 1) Добавляем пустой вариант в начало списка часовых поясов
        timezone_choices = list(self.fields["timezone"].choices)
        if not timezone_choices or timezone_choices[0][0] != "":
            self.fields["timezone"].choices = [
                ("", "Выберите часовой пояс"),
                *timezone_choices,
            ]

        # 2) Для гостя email нельзя блокировать read-only: это его первый ввод email в шаге подбора
        if not email_readonly:
            email_widget = self.fields["email"].widget
            email_widget.attrs.pop("readonly", None)
            email_widget.attrs["class"] = (
                "block w-full max-w-sm rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-lg "
                "text-gray-900 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm"
            )
            email_widget.attrs["placeholder"] = "Ваш email"

    def save(self, user):
        """Сохранение данных формы в модели AppUser и ClientProfile.
        Логика:
            1) Обновляем поля пользователя: first_name, age, timezone (email - только для чтения и НЕ обновляется).
            2) Обновляем client_profile.therapy_experience.
            3) Используем транзакцию, чтобы гарантировать целостность данных."""

        cleaned_data = self.cleaned_data

        with transaction.atomic():  # гарантировать целостность данных и случайно не сохранить только часть

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
