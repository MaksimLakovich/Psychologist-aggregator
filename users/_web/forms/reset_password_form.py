from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class PasswordResetRequestForm(forms.Form):
    """Форма для запроса восстановления пароля неавторизованным пользователем."""

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "name@email.com",
                "class": (
                    "block w-full rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-lg "
                    "text-gray-900 focus:border-indigo-600 focus:ring-indigo-600 shadow-sm"
                ),
                "autocomplete": "email",
            }
        ),
    )


class PasswordResetConfirmForm(forms.Form):
    """Форма для подтверждения сброса пароля через uid/token и установку нового пароля."""

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

    def clean(self):
        """Валидация совпадения паролей и проверка по Django Password Validators."""
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        new_password_confirm = cleaned_data.get("new_password_confirm")

        if new_password and new_password_confirm and new_password != new_password_confirm:
            self.add_error("new_password_confirm", "Пароли не совпадают.")
            return cleaned_data

        if new_password:
            try:
                validate_password(new_password)
            except ValidationError as exc:
                self.add_error("new_password", exc)

        return cleaned_data
