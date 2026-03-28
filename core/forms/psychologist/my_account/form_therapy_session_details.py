from django import forms


class PsychologistTherapySessionDetailsForm(forms.Form):
    """Форма редактирования деталей терапевтической сессии со стороны специалиста.

    Бизнес-смысл:
        - специалист отвечает за организационную часть встречи и поэтому может управлять ссылкой на созвон;
        - meeting_resume нужен для краткого протокола или итогов уже проведенной встречи,
          которые потом смогут прочитать все участники завершенного слота.
    """

    # TODO: Временно такой набор, но при реализации страницы для специалиста необходимо будет наследоваться от
    #  ForumMessageForm для внедрения функционала "ФОРУМ" внутри страницы и т.д.
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
    meeting_resume = forms.CharField(
        required=False,
        label="Итоги встречи",
        widget=forms.Textarea(
            attrs={
                "class": "w-full rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-800 "
                         "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                # "rows" у Textarea означает начальную видимую высоту поля в 4 строки текста в браузере. Т.е.,
                # это не ограничение на количество строк в сообщении, а просто настройка изначальной видимости строк
                "rows": 6,
                "placeholder": "Кратко опишите резюме встречи, договоренности или результаты проведенной встречи",
            }
        ),
    )
