from django import forms
from django.core.exceptions import ValidationError

from users.constants import (AGE_BUCKET_CHOICES, GENDER_CHOICES,
                             PREFERRED_TOPIC_TYPE_CHOICES)
from users.models import Method, Topic


class ClientPersonalQuestionsForm(forms.Form):
    """Кастомная форма для страницы *Персональные вопросы*.
    Форма объединяет данные из разных моделей: Method, Topic, AppUser и PsychologistProfile/ClientProfile.
    Основная логика:
        - При GET форма получает initial-значения из связанных моделей, чтобы пользователь сразу видел
         уже заполненные данные.
        - При POST форма валидирует и сохраняет обновленные данные. Это стандартный механизм дополняет AJAX
        для автосохранения (решает вопрос fallback, если вдруг AJAX сломается). Эти два механизма не конфликтуют,
        а дополняют друг друга, создавая надежную систему."""

    preferred_topic_type = forms.ChoiceField(
        choices=PREFERRED_TOPIC_TYPE_CHOICES,
        required=True  # обязателен, т.к. модель имеет default
    )
    requested_topics = forms.ModelMultipleChoiceField(
        queryset=Topic.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple  # в html-шаблоне мы рендерим руками, так что widget не обязателен тут
    )
    has_preferences = forms.BooleanField(
        required=False
    )
    preferred_ps_gender = forms.MultipleChoiceField(
        choices=GENDER_CHOICES,
        required=False,
        widget=forms.MultipleHiddenInput  # в html-шаблоне мы рендерим руками, так что widget не обязателен тут
    )
    preferred_ps_age = forms.MultipleChoiceField(
        choices=AGE_BUCKET_CHOICES,
        required=False,
        widget=forms.MultipleHiddenInput  # в html-шаблоне мы рендерим руками, так что widget не обязателен тут
    )
    preferred_methods = forms.ModelMultipleChoiceField(
        queryset=Method.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple  # в html-шаблоне мы рендерим руками, так что widget не обязателен тут
    )
    has_time_preferences = forms.BooleanField(
        required=False
    )

    def clean(self):
        """Метод clean в форме это как пограничный контроль. Задача метода: проверить, не пытаются ли данные
        "протащить" через форму что-то недопустимое или логически противоречивое."""
        # Django сначала сам собирает и проверяет все поля.
        # В итоге получаем словарь cleaned_data с уже "почищенными" значениями
        cleaned_data = super().clean()
        preferred_topic_type = cleaned_data.get("preferred_topic_type")
        requested_topics = cleaned_data.get("requested_topics")

        # Если тип не выбран - то ничего не делаем. Просто возвращаем данные как есть
        if not preferred_topic_type:
            return cleaned_data

        # В Django CHOICES обычно просто список кортежей вида [("key", "Value")]. Превращаем его в удобный словарь,
        # чтоб можно было использовать например метод get(), которого нет у кортежей.
        # Пример: Из ["individual", "Индивидуальная"] получаем {"individual", "Индивидуальная"}
        topic_type_map = dict(PREFERRED_TOPIC_TYPE_CHOICES)
        # В expected_topic_type записывается - "Индивидуальная"
        expected_topic_type = topic_type_map.get(preferred_topic_type)

        # Если вдруг пришел какой-то странный код типа темы, которого нет у нас, то просто возвращаем данные как есть
        if not expected_topic_type:
            return cleaned_data

        # Если тем нет (None) - то создаем пустой набор
        if requested_topics is None:
            requested_topics = Topic.objects.none()

        # ИТОГ. Проверяем: есть ли темы именно выбранного типа
        selected_for_type = requested_topics.filter(type=expected_topic_type)

        if selected_for_type.count() == 0:
            self.add_error("requested_topics", ValidationError("Пожалуйста, отметьте хотя бы одну тему"))

        return cleaned_data
