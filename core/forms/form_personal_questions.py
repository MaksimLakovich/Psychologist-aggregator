from django import forms

from users.models import Method


class ClientPersonalQuestionsForm(forms.Form):
    """Кастомная форма для страницы *Персональные вопросы*.
    Форма объединяет данные из разных моделей: Method, Topic, AppUser и PsychologistProfile/ClientProfile.
    Основная логика:
        - При GET форма получает initial-значения из связанных моделей, чтобы пользователь сразу видел
         уже заполненные данные.
        - При POST форма валидирует и сохраняет обновленные данные (этот стандартный механизм дополняет AJAX
        для автосохранения (решает вопрос fallback, если вдруг AJAX сломается). Эти два механизма не конфликтуют,
        а дополняют друг друга, создавая надежную систему."""

    has_preferences = forms.BooleanField(
        required=False
    )

    preferred_methods = forms.ModelMultipleChoiceField(
        queryset=Method.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple  # в html-шаблоне мы рендерим руками, так что widget не обязателен тут
    )
