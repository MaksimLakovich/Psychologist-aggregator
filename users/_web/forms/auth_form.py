from django import forms
from django.contrib.auth.forms import AuthenticationForm

from users.models import AppUser


class AppUserRegistrationForm(forms.ModelForm):
    """Форма для регистрации нового пользователя.
    В widget используются Tailwind/Flowbite-классы."""

    # Шаг 1: Объявляем немодельные поля (их нужно описать явно перед Meta)
    password1 = forms.CharField(
        label="Придумайте пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "class": (
                    "bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg "
                    "focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 "
                    "dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                ),
                "autocomplete": "new-password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Повторите пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "class": (
                    "bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg "
                    "focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 "
                    "dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                ),
                "autocomplete": "new-password",
            }
        ),
    )

    # Шаг 2: Объявляем поля из модели данных
    class Meta:
        model = AppUser
        fields = ("email", "first_name", "age")
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "name@email.com",
                    "class": (
                        "bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg "
                        "focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 "
                        "dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                    ),
                    "autocomplete": "email",
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "Укажите ваше имя",
                    "class": (
                        "bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg "
                        "focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 "
                        "dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                    ),
                    "autocomplete": "given-name",
                }
            ),
            "age": forms.NumberInput(
                attrs={
                    "placeholder": "Укажите ваш возраст",
                    "class": (
                        "bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg "
                        "focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 "
                        "dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                    ),
                    "min": 18,
                    "max": 120,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Убираем help_text, чтобы не шуметь на странице."""
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.help_text = None

    def clean(self):
        """Метод clean в форме это как пограничный контроль. Задача метода: проверить, не пытаются ли данные
        "протащить" через форму что-то недопустимое или логически противоречивое."""
        # Django сначала сам собирает и проверяет все поля.
        # В итоге получаем словарь cleaned_data с уже "почищенными" значениями
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Пароли не совпадают.")

        return cleaned_data

    def validate_unique(self):
        """Отключаем стандартную уникальность для email, которая установлена в модели, чтобы потом можно было
        защититься от user-enumeration (т.е., отправлять нейтральные ответы и не сообщать, что он уже есть):
            - если проверять уникальность прямо на форме, то мы скажем пользователю "такой email уже есть";
            - поэтому: мы отключаем validate_unique() и задаем нейтральный во вьюхе."""
        return


class AppUserLoginForm(AuthenticationForm):
    """Форма для авторизации ранее зарегистрированного пользователя.
    В widget используются Tailwind/Flowbite-классы."""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "name@email.com",
                "class": (
                    "bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg "
                    "focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 "
                    "dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                ),
                "autocomplete": "email",
            }
        ),
    )

    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "class": (
                    "bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg "
                    "focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 "
                    "dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                ),
                "autocomplete": "current-password",
            }
        ),
    )


# class UserProfileEditForm(forms.ModelForm):
#     """Форма для редактирования профиля зарегистрированного пользователя на сайте магазина."""
#
#     class Meta:
#         model = UserCustomer
#         fields = (
#             "email",
#             "avatar",
#             "first_name",
#             "last_name",
#             "phone_number",
#             "country",
#         )
#         widgets = {
#             "email": forms.EmailInput(
#                 attrs={"readonly": "readonly"}
#             ),  # Email нельзя редактировать (readonly)
#             "avatar": forms.FileInput(),
#             "first_name": forms.TextInput(attrs={"placeholder": "Введите имя"}),
#             "last_name": forms.TextInput(attrs={"placeholder": "Введите фамилию"}),
#             "phone_number": forms.TextInput(
#                 attrs={"placeholder": "Введите номер телефона"}
#             ),
#             "country": forms.TextInput(
#                 attrs={"placeholder": "Укажите страну проживания"}
#             ),
#         }
#
#     def __init__(self, *args, **kwargs):
#         """1) Добавляем CSS-классы ко всем полям формы. 2) Убираем 'help_text' для всех полей."""
#         super().__init__(*args, **kwargs)
#         for field_name, field in self.fields.items():
#             field.help_text = None
#             if not isinstance(field.widget, forms.CheckboxInput):
#                 field.widget.attrs["class"] = "form-control"
#
#
# class UserPasswordChangeForm(PasswordChangeForm):
#     """Форма для смены пароля пользователя."""
#
#     def __init__(self, *args, **kwargs):
#         """Добавляем CSS-классы и placeholders к полям смены пароля."""
#         super().__init__(*args, **kwargs)
#         for field_name, field in self.fields.items():
#             field.widget.attrs["class"] = "form-control"
#             field.help_text = None
#         self.fields["old_password"].widget.attrs[
#             "placeholder"
#         ] = "Введите текущий пароль"
#         self.fields["new_password1"].widget.attrs[
#             "placeholder"
#         ] = "Введите новый пароль"
#         self.fields["new_password2"].widget.attrs[
#             "placeholder"
#         ] = "Подтвердите новый пароль"
