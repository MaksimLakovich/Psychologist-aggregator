from aggregator._web.selectors.psychologist_selectors import \
    filter_by_topic_type
from aggregator._web.services.topic_type_mapping import \
    CLIENT_TO_TOPIC_TYPE_MAP

# Используем уже существующий mapping-слой как единый источник истины для допустимых ключей фильтра "Вид консультации"
CONSULTATION_TYPE_CHOICES = CLIENT_TO_TOPIC_TYPE_MAP


# 1. Фильтр "Вид консультации": фильтрация по ТИПУ тем (Индивидуальная/Парная)

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


# 2. Фильтр "Симптомы": фильтрация по конкретным ТЕМАМ

def extract_topic_ids(raw_values):
    """Возвращает нормализованный список выбранных topic-id для фильтра "Симптомы".

    Простая логика:
        - принимаем список строк/чисел;
        - оставляем только положительные целые id;
        - убираем дубли, сохраняя исходный порядок.

    Почему здесь возвращаем список строк:
        - во frontend state и в DOM нам удобнее работать со строками;
        - в Django-фильтре topics__in строки id тоже безопасно преобразуются в числа.
    """
    # Если на вход пришел не список и не кортеж (а, например, одна строка или None), функция сразу
    # возвращает пустой список, чтобы не вызвать ошибку дальше
    if not isinstance(raw_values, (list, tuple)):
        return []

    # Это итоговый список. Мы используем список, чтобы сохранить порядок появления ID
    normalized_topic_ids = []
    # Это "черновик" для уникальных значений. Поиск в set (множестве) происходит мгновенно, это эффективнее,
    # чем проверять наличие дубликатов в списке
    seen_topic_ids = set()

    for raw_value in raw_values:
        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError):
            continue

        if parsed_value <= 0:
            continue

        # Превращаем проверенное число обратно в строку. Как указано в docstrings, это нужно для удобства фронтенда
        # и совместимости с Django-фильтрами
        normalized_value = str(parsed_value)
        if normalized_value in seen_topic_ids:
            continue

        seen_topic_ids.add(normalized_value)
        normalized_topic_ids.append(normalized_value)

    return normalized_topic_ids


def filter_topics(queryset, topic_ids):
    """Применяет к QuerySet фильтр "Симптомы".

    Если topic_ids пустой список:
        - фильтр не активен;
        - возвращаем исходный QuerySet без сужения выдачи.

    Если topic_ids заполнен:
        - оставляем психологов, у которых есть хотя бы одна из выбранных тем.

    Важный момент:
        - здесь используется логика OR, а не AND.
        - То есть если клиент выбрал 3 симптома, психолог попадет в выдачу,
          если у него в профиле есть хотя бы один из этих симптомов.
    """
    normalized_topic_ids = extract_topic_ids(topic_ids)
    if not normalized_topic_ids:
        return queryset

    # distinct гарантирует, что считаем уникальные связанные темы
    return queryset.filter(topics__in=normalized_topic_ids).distinct()


# ЗАПУСК ФИЛЬТРАЦИИ

def apply_catalog_basic_filters(queryset, filters_state):
    """Агрегирует базовые фильтры каталога и применяет их к QuerySet.

    На текущем шаге подключены фильтры:
        - consultation_type.
        - topic_ids.

    Формат filters_state:
        {
            "consultation_type": "individual" | "couple" | None,
            "topic_ids": ["1", "2"] | [],
        }
    """
    if not isinstance(filters_state, dict):
        filters_state = {}

    consultation_type = extract_consultation_type(
        filters_state.get("consultation_type")
    )
    topic_ids = extract_topic_ids(filters_state.get("topic_ids"))

    queryset = filter_topic_type(queryset, consultation_type)
    queryset = filter_topics(queryset, topic_ids)

    return queryset
