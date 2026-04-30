from django import forms

from core.forms.forum_message.form_forum_message import ForumMessageForm


class PsychologistTherapySessionDetailsForm(ForumMessageForm):
    """Форма редактирования деталей терапевтической сессии со стороны специалиста.

    Бизнес-смысл:
        - специалист отвечает за организационную часть встречи и поэтому может управлять ссылкой на созвон;
        - meeting_resume нужен для краткого протокола или итогов уже проведенной встречи,
          которые потом смогут прочитать все участники завершенного слота.
        - форумные поля наследуются от ForumMessageForm, чтобы специалист и клиент работали с единым
          input-contract сообщений внутри встречи.
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
    event_description = forms.CharField(
        required=False,
        label="Описание события",
        widget=forms.Textarea(
            attrs={
                "class": "w-full rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-800 "
                         "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                # "rows" у Textarea означает начальную видимую высоту поля в 4 строки текста в браузере. Т.е.,
                # это не ограничение на количество строк в сообщении, а просто настройка изначальной видимости строк
                "rows": 4,
                "placeholder": "Добавьте описание встречи, которое увидит клиент",
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
                "placeholder": "Кратко опишите резюме встречи, договоренности или результаты проведенной встречи",
            }
        ),
    )
