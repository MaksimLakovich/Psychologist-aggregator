from django import forms


class ForumMessageForm(forms.Form):
    """Универсальная форма forum-сообщения внутри разных типов событий.

    Бизнес-смысл:
        - форумные сообщения больше не относятся только к терапии и не должны жить в client-модуле;
        - одна и та же форма нужна и клиенту, и специалисту, и в других типах событий или отдельном
          межпользовательском общении.
    """

    ACTION_CHOICES = [
        ("add_message", "Добавить сообщение"),
        ("edit_message", "Редактировать сообщение"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        initial="add_message",
        widget=forms.HiddenInput(),
    )
    message_id = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(),
    )
    message = forms.CharField(
        required=True,
        label="Сообщение",
        widget=forms.Textarea(
            attrs={
                "class": "w-full rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-800 "
                         "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                # "rows" у Textarea означает начальную видимую высоту поля в 4 строки текста в браузере. Т.е.,
                # это не ограничение на количество строк в сообщении, а просто настройка изначальной видимости строк
                "rows": 4,
                "placeholder": "Напишите ваше сообщение",
            }
        ),
    )

    def clean_message(self):
        """Очищает текст сообщения от пустых значений из одних пробелов.

        Для форумного сценария пустое сообщение не имеет смысла, даже если HTML-форма формально его отправила.
        """
        message = (self.cleaned_data.get("message") or "").strip()
        if not message:
            raise forms.ValidationError("Введите текст сообщения")
        return message
