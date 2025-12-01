from django import forms
from django.contrib.auth.forms import AuthenticationForm


class AppUserLoginForm(AuthenticationForm):
    """Форма авторизации с Tailwind/Flowbite-классами на виджетах
    для входа ранее зарегистрированного пользователя системы."""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "name@company.com",
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
