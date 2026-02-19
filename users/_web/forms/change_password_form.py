from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class ChangePasswordForm(forms.Form):
    """Форма для смены пароля авторизованного пользователя."""

    current_password = forms.CharField(
        label="Текущий пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "class": (
                    "block w-full rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-lg "
                    "text-gray-900 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm"
                ),
                "autocomplete": "current-password",
            }
        ),
    )
    new_password = forms.CharField(
        label="Новый пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "class": (
                    "block w-full rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-lg "
                    "text-gray-900 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm"
                ),
                "autocomplete": "new-password",
            }
        ),
    )
    new_password_confirm = forms.CharField(
        label="Повторите новый пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "class": (
                    "block w-full rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-lg "
                    "text-gray-900 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm"
                ),
                "autocomplete": "new-password",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        """Принимаем пользователя, чтобы проверить текущий пароль."""
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        """Проверяем текущий пароль и валидируем новый (проверяем совпадение в новом пароле и параллельно
        выполняем валидацию нового пароля через Django Password Validators)."""
        cleaned_data = super().clean()
        current_password = cleaned_data.get("current_password")
        new_password = cleaned_data.get("new_password")
        new_password_confirm = cleaned_data.get("new_password_confirm")

        # Проверяем текущий пароль
        if self.user and current_password:
            if not self.user.check_password(current_password):
                self.add_error("current_password", "Текущий пароль указан неверно.")

        # Проверяем совпадение новых паролей
        if new_password and new_password_confirm and new_password != new_password_confirm:
            self.add_error("new_password_confirm", "Пароли не совпадают.")
            return cleaned_data

        # Проверяем новый пароль через Django Password Validators
        if new_password:
            try:
                validate_password(new_password, user=self.user)
            except ValidationError as exc:
                self.add_error("new_password", exc)

        return cleaned_data
