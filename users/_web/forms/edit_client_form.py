from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from timezone_field import TimeZoneFormField

from users.models import AppUser


BASE_INPUT_CLASS = (
    "block w-full rounded-xl border border-gray-100 bg-white px-4 py-3 text-lg "
    "text-zinc-800 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm"
)
READONLY_INPUT_CLASS = (
    "block w-full rounded-xl border border-gray-100 bg-gray-100 px-4 py-3 text-lg "
    "text-zinc-500 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm"
)
READONLY_SELECT_CLASS = (
    "block w-full rounded-xl border border-gray-100 bg-gray-100 px-4 py-3 text-lg "
    "text-zinc-500 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm "
    "opacity-100 disabled:opacity-100 disabled:text-zinc-500 disabled:bg-gray-100 disabled:border-gray-100"
)


class EditClientProfileForm(forms.ModelForm):
    """Форма для редактирования профиля клиента."""

    class Meta:
        model = AppUser
        fields = ("first_name", "last_name", "age", "email", "phone_number", "timezone")
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "Имя",
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Фамилия",
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "autocomplete": "family-name",
                }
            ),
            "age": forms.NumberInput(
                attrs={
                    "placeholder": "Возраст",
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "min": 18,
                    "max": 120,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "name@email.com",
                    "readonly": "readonly",
                    "class": (
                        "block w-full rounded-xl border border-gray-100 bg-gray-100 px-4 py-3 text-lg "
                        "text-zinc-500 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm "
                        "cursor-not-allowed"
                    ),
                    "data-view-class": (
                        "block w-full rounded-xl border border-gray-100 bg-gray-100 px-4 py-3 text-lg "
                        "text-indigo-700 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm "
                        "cursor-not-allowed"
                    ),
                    "autocomplete": "email",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "placeholder": "+7XXXXXXXXXX",
                    "class": READONLY_INPUT_CLASS,
                    "data-view-class": READONLY_INPUT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "autocomplete": "tel",
                }
            ),
            "timezone": forms.Select(
                attrs={
                    "class": READONLY_SELECT_CLASS,
                    "data-view-class": READONLY_SELECT_CLASS,
                    "data-edit-class": BASE_INPUT_CLASS,
                    "style": "-webkit-text-fill-color: rgb(113 113 122);",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Убираем help_text и добавляем пустой вариант для timezone."""
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.help_text = None

        timezone_field = self.fields.get("timezone")
        if isinstance(timezone_field, TimeZoneFormField):
            timezone_choices = list(timezone_field.choices)
            if not timezone_choices or timezone_choices[0][0] != "":
                timezone_field.choices = [("", "Выберите часовой пояс"), *timezone_choices]

        # Дополнительная валидация возраста на уровне формы
        self.fields["age"].validators = [MinValueValidator(18), MaxValueValidator(120)]

    def clean_email(self):
        """Email не редактируется в этой форме: всегда возвращаем исходное значение."""
        if self.instance and self.instance.email:
            return self.instance.email

        return self.cleaned_data.get("email")

    def save(self, commit=True):
        """Сохраняем только разрешенные поля, email не меняем."""
        user = super().save(commit=False)
        user.email = self.instance.email

        if commit:
            user.save(update_fields=["first_name", "last_name", "age", "phone_number", "timezone"])

        return user
