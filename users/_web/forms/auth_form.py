from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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
        """Валидация совпадения паролей и проверка по Django Password Validators.
        Метод clean в форме это как пограничный контроль. Задача метода: проверить, не пытаются ли данные
        "протащить" через форму что-то недопустимое или логически противоречивое."""
        # Django сначала сам собирает и проверяет все поля.
        # В итоге получаем словарь cleaned_data с уже "почищенными" значениями
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Пароли не совпадают.")

        if password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                self.add_error("password1", exc)

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

    def clean(self):
        """Кастомная обработка авторизации для вывода понятного сообщения при is_active=False.
        То есть, когда пользователь зарегистрировался, не подтвердил почту, но пытается выполнить вход, то мы
        выводим понятное сообщение о том, что нужно сделать."""
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)

            if self.user_cache is None:
                user = AppUser.objects.filter(email=username).first()
                if user and user.check_password(password) and not user.is_active:
                    raise ValidationError(
                        "Пожалуйста, проверьте почту и завершите подтверждение регистрации."
                    )
                raise self.get_invalid_login_error()

            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
