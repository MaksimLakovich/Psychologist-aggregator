from django import forms

from calendar_engine.booking.validators import parse_requested_slot_start
from users.constants import PREFERRED_TOPIC_TYPE_CHOICES


class ClientAddPaymentCardForm(forms.Form):
    """Кастомная форма для страницы *Завершение записи и добавление платежной карты*.

    Уточнения:
    - На текущем этапе страница пока не сохраняет реальные банковские карты, а использует submit как точку
      подтверждения бронирования;
    - Поэтому форма хранит только скрытые booking-поля, которые заполняются из выбора специалиста и слота.

    HiddenInput() означает:
    - поле существует в форме и его значение отправляется на backend, но пользователь не видит его как обычное поле;
    - на шаге выбора специалиста клиент уже выбрал: specialist_profile_id, slot_start_iso, consultation_type и поэтому
      на странице payment-card он уже не должен выбирать их повторно.
    """

    specialist_profile_id = forms.IntegerField(
        required=True,
        widget=forms.HiddenInput(),
    )
    slot_start_iso = forms.CharField(
        required=True,
        widget=forms.HiddenInput(),
    )
    consultation_type = forms.ChoiceField(
        required=True,
        choices=PREFERRED_TOPIC_TYPE_CHOICES,
        widget=forms.HiddenInput(),
    )

    def clean_slot_start_iso(self):
        """Проверяет, что скрытое поле слота содержит валидный aware ISO datetime.

        Бизнес-смысл:
            - payment-card это уже шаг подтверждения, а не выбора времени;
            - slot_start_iso приходит из frontend и НЕ должен приниматься БЕЗ проверки,
              чтоб случайно backend не принял пустой или сломанный slot_start_iso;
            - фактическая перепроверка доступности слота будет выполнена use-case.
        """
        slot_start_iso = self.cleaned_data["slot_start_iso"]
        parse_requested_slot_start(slot_start_iso=slot_start_iso)

        return slot_start_iso
