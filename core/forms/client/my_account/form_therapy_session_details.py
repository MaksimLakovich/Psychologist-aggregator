from django import forms

from core.forms.forum_message.form_forum_message import ForumMessageForm


class ClientTherapySessionDetailsForm(ForumMessageForm):
    """Форма для редактирования доступных клиенту деталей уже созданной терапевтической сессии.
    Наследуемся от ForumMessageForm - тем самым накладываем на форум функционал страницы клиента.

    Бизнес-смысл:
        - после выноса forum-сообщений в отдельный shared-модуль сам input-contract живет в ForumMessageForm;
        - этот класс оставляем как тонкую обертку, чтобы аккуратно пережить рефакторинг
          и не сломать возможные старые импорты client-модуля + могут появиться для клиента доступные для
          редактирования поля (например, "Добавить заметку" и тд) и форма нужна будет.
    """

    # TODO: Временно pass, но изменим после того как будет реализован функционал "Добавить заметку" и т.д.
    pass


class CancelTherapySessionForm(forms.Form):
    """Форма отмены текущей встречи клиентом."""

    action = forms.ChoiceField(
        choices=[("cancel_session", "Отменить встречу")],
        widget=forms.HiddenInput(),
    )
    cancel_reason_type = forms.ChoiceField(
        choices=[("cancelled_by_user", "Отменено пользователем")],
        initial="cancelled_by_user",
        widget=forms.HiddenInput(),
    )
    cancel_reason = forms.CharField(
        required=True,
        label="Причина отмены",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Кратко опишите, почему хотите отменить встречу",
            }
        ),
    )

    def clean_cancel_reason(self):
        cancel_reason = (self.cleaned_data.get("cancel_reason") or "").strip()
        if not cancel_reason:
            raise forms.ValidationError("Для отмены встречи нужно указать причину")
        return cancel_reason


class RescheduleTherapySessionForm(forms.Form):
    """Форма переноса встречи на новый слот."""

    action = forms.ChoiceField(
        choices=[("reschedule_session", "Перенести встречу")],
        widget=forms.HiddenInput(),
    )
    cancel_reason_type = forms.ChoiceField(
        choices=[("rescheduled", "Перенесено")],
        initial="rescheduled",
        widget=forms.HiddenInput(),
    )
    cancel_reason = forms.CharField(
        required=True,
        label="Причина переноса",
        widget=forms.Textarea(
            attrs={
                "id": "id_reschedule_cancel_reason",
                "rows": 4,
                "placeholder": "Кратко опишите, почему хотите перенести встречу и укажите новое "
                               "предпочитаемое время в расписании специалиста",
            }
        ),
    )
    previous_event_id = forms.UUIDField(
        required=True,
        widget=forms.HiddenInput(),
    )
    slot_start_iso = forms.CharField(
        required=True,
        widget=forms.HiddenInput(),
    )

    def clean_cancel_reason(self):
        cancel_reason = (self.cleaned_data.get("cancel_reason") or "").strip()
        if not cancel_reason:
            raise forms.ValidationError("Для переноса встречи нужно указать причину")
        return cancel_reason

    def clean_slot_start_iso(self):
        slot_start_iso = (self.cleaned_data.get("slot_start_iso") or "").strip()
        if not slot_start_iso:
            raise forms.ValidationError("Выберите новый слот для переноса встречи")
        return slot_start_iso
