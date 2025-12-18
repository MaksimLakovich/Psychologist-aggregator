from django import forms


class ClientChoicePsychologistForm(forms.Form):
    """Кастомная форма для страницы *Выбор психолога*.
    Форма объединяет данные из разных моделей: Method, Topic, AppUser и PsychologistProfile / ClientProfile.
    Основная логика:
        - При GET форма получает initial-значения из связанных моделей, чтобы клиент сразу
        видел данные в карточке психологов.
        - При POST форма валидирует и сохраняет данные о бронировании слота в календаре психолога.
    """

    # TODO: дополнить в docstrings описание о post: после реализации приложения calendar появятся слоты и бронирование
    pass
