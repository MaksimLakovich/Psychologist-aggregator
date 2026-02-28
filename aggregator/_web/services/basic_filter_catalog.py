from aggregator._web.selectors.psychologist_selectors import filter_by_topic_type
from aggregator._web.services.topic_type_mapping import CLIENT_TO_TOPIC_TYPE_MAP

# Используем уже существующий mapping-слой как единый источник истины для допустимых ключей фильтра "Вид консультации"
CONSULTATION_TYPE_CHOICES = CLIENT_TO_TOPIC_TYPE_MAP


def extract_consultation_type(raw_value):
    """Возвращает валидное значение фильтра "Вид консультации" или None.

    Простая логика:
        - если ключ есть в CLIENT_TO_TOPIC_TYPE_MAP, возвращаем его как есть;
        - если ключ пустой или невалидный, возвращаем None.

    Значение None здесь означает:
        - фильтр не выбран;
        - в каталоге нужно показывать всех психологов.
    """
    if raw_value in CONSULTATION_TYPE_CHOICES:
        return raw_value
    return None


def filter_topic_type(queryset, consultation_type):
    """Применяет к QuerySet фильтр "Вид консультации".

    Если consultation_type=None:
        - фильтр не активен;
        - возвращаем исходный QuerySet без сужения выдачи.

    Если consultation_type валиден:
        - переиспользуем существующую selector-функцию filter_by_topic_type(),
          чтобы не дублировать SQL-логику.
    """
    if not consultation_type:
        return queryset

    return filter_by_topic_type(queryset, consultation_type)


def build_consultation_type_counts(queryset):
    """Считает количество психологов для вариантов фильтра "Вид консультации".

    Возвращаем словарь вида:
        {
            "all": 40,
            "individual": 39,
            "couple": 4,
        }

    Эти числа нужны в модалке фильтра, чтобы сразу показывать пользователю,
    сколько карточек он увидит после нажатия кнопки "Показать результаты".
    """
    return {
        "all": queryset.count(),
        "individual": filter_by_topic_type(queryset, "individual").count(),
        "couple": filter_by_topic_type(queryset, "couple").count(),
    }


def apply_catalog_basic_filters(queryset, filters_state):
    """Агрегирует базовые фильтры каталога и применяет их к QuerySet.

    На текущем шаге подключен только один фильтр:
        - consultation_type.

    Формат filters_state:
        {"consultation_type": "individual" | "couple" | None}
    """
    if not isinstance(filters_state, dict):
        filters_state = {}

    consultation_type = extract_consultation_type(
        filters_state.get("consultation_type")
    )

    queryset = filter_topic_type(queryset, consultation_type)
    return queryset
