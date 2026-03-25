from django import forms


class PsychologistTherapySessionDetailsForm(forms.Form):
    """Форма редактирования деталей терапевтической сессии со стороны специалиста.

    Бизнес-смысл:
        - специалист отвечает за организационную часть встречи и поэтому может управлять ссылкой на созвон;
        - comment пока остается общим простым полем заметки к сессии до появления отдельной модели
          форумного обсуждения для участников TimeSlot;
        - meeting_resume нужен для краткого протокола или итогов уже проведенной встречи,
          которые потом смогут прочитать все участники завершенного слота.
    """

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
    meeting_resume = forms.CharField(
        required=False,
        label="Итоги встречи",
        widget=forms.Textarea(
            attrs={
                "class": "w-full rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-800 "
                         "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                "rows": 6,
                "placeholder": "Кратко опишите выводы, договоренности, результаты или протокол проведенной встречи.",
            }
        ),
    )
