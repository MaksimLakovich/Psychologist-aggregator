from django import forms


class ClientTherapySessionDetailsForm(forms.Form):
    """Форма для редактирования доступных клиенту деталей уже созданной терапевтической сессии.

    На текущем этапе клиент может обновлять только те поля слота, которые не ломают booking-модель:
        - meeting_url: ссылка на комнату/созвон;
        - comment: дополнительный комментарий к сессии.

    Почему именно так:
        - это безопасные поля для первого detail-screen;
        - изменение даты, времени, статусов и участников требует отдельного полноценного use-case;
        - здесь даем минимально полезный и уже реальный editing-flow без нарушения бизнес-инвариантов.
    """

    # TODO: Убрать meeting_url у клиента потом. Это должно быть только у специалиста
    meeting_url = forms.URLField(
        required=False,
        label="Ссылка на сессию",
        widget=forms.URLInput(
            attrs={
                "class": "w-full rounded-xl border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-800 "
                         "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                "placeholder": "https://...",
            }
        ),
    )
    comment = forms.CharField(
        required=False,
        label="Комментарий к сессии",
        widget=forms.Textarea(
            attrs={
                "class": "w-full rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-800 "
                         "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                "rows": 5,
                "placeholder": "Например: ссылка на материалы, уточнение по подготовке или важная заметка к сессии.",
            }
        ),
    )
