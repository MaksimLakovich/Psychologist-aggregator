from datetime import date

from django.db.models import Q

from aggregator._web.selectors.psychologist_selectors import \
    filter_by_topic_type
from aggregator._web.services.topic_type_mapping import \
    CLIENT_TO_TOPIC_TYPE_MAP
from users.constants import GENDER_CHOICES

# Используем уже существующий mapping-слой как единый источник истины для допустимых ключей фильтра "Вид консультации"
CONSULTATION_TYPE_CHOICES = CLIENT_TO_TOPIC_TYPE_MAP
DEFAULT_CATALOG_AGE_MIN = 18
DEFAULT_CATALOG_AGE_MAX = 120
DEFAULT_CATALOG_EXPERIENCE_MIN = 0
DEFAULT_CATALOG_EXPERIENCE_MAX = max(date.today().year - 1900, 0)
ALLOWED_GENDER_VALUES = {value for value, _label in GENDER_CHOICES}


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


# 3. Фильтр "Подход": фильтрация по выбранным методам психолога

def extract_method_ids(raw_values):
    """Возвращает нормализованный список выбранных method-id для фильтра "Подход".

    Простая логика:
        - принимаем список строк/чисел;
        - оставляем только положительные целые id;
        - убираем дубли, сохраняя исходный порядок.

    Почему здесь возвращаем список строк:
        - во frontend state и в DOM нам удобнее работать со строками;
        - в Django-фильтре methods__in строки id тоже безопасно преобразуются в числа.
    """
    if not isinstance(raw_values, (list, tuple)):
        return []

    normalized_method_ids = []
    seen_method_ids = set()

    for raw_value in raw_values:
        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError):
            continue

        if parsed_value <= 0:
            continue

        normalized_value = str(parsed_value)
        if normalized_value in seen_method_ids:
            continue

        seen_method_ids.add(normalized_value)
        normalized_method_ids.append(normalized_value)

    return normalized_method_ids


def filter_methods(queryset, method_ids):
    """Применяет к QuerySet фильтр "Подход".

    Если method_ids пустой список:
        - фильтр не активен;
        - возвращаем исходный QuerySet без сужения выдачи.

    Если method_ids заполнен:
        - оставляем психологов, у которых есть хотя бы один из выбранных методов.

    Важный момент:
        - здесь используется логика OR, а не AND.
        - То есть если клиент выбрал 3 подхода, психолог попадет в выдачу,
          если у него в профиле есть хотя бы один из этих подходов.
    """
    normalized_method_ids = extract_method_ids(method_ids)
    if not normalized_method_ids:
        return queryset

    return queryset.filter(methods__in=normalized_method_ids).distinct()


# 4. Фильтр "Возраст": фильтрация по возрасту психолога

def extract_age_range(raw_age_min, raw_age_max, age_bounds=None):
    """Возвращает безопасный диапазон возраста для фильтра "Возраст".

    Простая логика:
        - берем возрастные границы каталога (min/max) из БД или из fallback-констант;
        - пытаемся преобразовать входные значения в целые числа;
        - если значение выходит за границы каталога, прижимаем его к этим границам;
        - если после нормализации выбран весь диапазон целиком, возвращаем (None, None),
          то есть считаем фильтр неактивным.

    Значения None здесь означают:
        - возрастной фильтр не выбран;
        - каталог должен показывать специалистов любого возраста.
    """
    age_bounds = age_bounds or {}
    bounds_min = age_bounds.get("min", DEFAULT_CATALOG_AGE_MIN)
    bounds_max = age_bounds.get("max", DEFAULT_CATALOG_AGE_MAX)

    # Шаг 1: Инициализируем границы.
    # Если в age_bounds пусто, то берутся значения которые установлены по умолчанию (DEFAULT_CATALOG_AGE_MIN/MAX)
    try:
        bounds_min = int(bounds_min)
    except (TypeError, ValueError):
        bounds_min = DEFAULT_CATALOG_AGE_MIN

    try:
        bounds_max = int(bounds_max)
    except (TypeError, ValueError):
        bounds_max = DEFAULT_CATALOG_AGE_MAX

    # Шаг 2: Страховка на случай, если кто-то перепутал границы местами (например, min=50, max=20), то меняем местами
    if bounds_min > bounds_max:
        bounds_min, bounds_max = bounds_max, bounds_min

    def parse_age_value(raw_value):
        """Внутренняя вспомогательная функция для обработки конкретного числа, введенного пользователем."""
        # 1) Если поле пустое, возвращаем None (значит, пользователь не ограничивал этот край)
        if raw_value in {"", None}:
            return None

        # 2) Пытается превратить ввод пользователя в число. Если ввели "привет", фильтр просто игнорируется (None)
        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError):
            return None

        # 3) Прижимает значения по краям: если пользователь хочет найти психолога 12 лет,
        # а min_age в системе 18 - то ставится 18. Если хочет 200-го соответственно ставится максимум (например, 99)
        if parsed_value < bounds_min:
            return bounds_min

        if parsed_value > bounds_max:
            return bounds_max

        return parsed_value

    age_min = parse_age_value(raw_age_min)
    age_max = parse_age_value(raw_age_max)

    if age_min is not None and age_max is not None and age_min > age_max:
        age_min, age_max = age_max, age_min

    if age_min == bounds_min:
        age_min = None

    if age_max == bounds_max:
        age_max = None

    return age_min, age_max


def filter_age(queryset, age_min, age_max):
    """Применяет к QuerySet фильтр "Возраст".

    Если age_min и age_max одновременно равны None:
        - фильтр не активен;
        - возвращаем исходный QuerySet без сужения выдачи.

    Если передан age_min:
        - оставляем психологов не младше указанного возраста.

    Если передан age_max:
        - оставляем психологов не старше указанного возраста.
    """
    if age_min is None and age_max is None:
        return queryset

    if age_min is not None:
        queryset = queryset.filter(user__age__gte=age_min)

    if age_max is not None:
        queryset = queryset.filter(user__age__lte=age_max)

    return queryset


# 5. Фильтр "Пол": фильтрация по полу психолога

def extract_gender(raw_value):
    """Возвращает валидное значение фильтра "Пол" или None.

    Простая логика:
        - если ключ есть в справочнике GENDER_CHOICES, возвращаем его как есть;
        - если ключ пустой или невалидный, возвращаем None.

    Значение None здесь означает:
        - фильтр пола не выбран;
        - в каталоге нужно показывать и мужчин, и женщин.
    """
    if raw_value in ALLOWED_GENDER_VALUES:
        return raw_value
    return None


def filter_gender(queryset, gender):
    """Применяет к QuerySet фильтр "Пол".

    Если gender=None:
        - фильтр не активен;
        - возвращаем исходный QuerySet без сужения выдачи.

    Если gender валиден:
        - оставляем только психологов указанного пола.
    """
    if not gender:
        return queryset

    return queryset.filter(gender=gender)


# 6. Фильтр "Цена": фильтрация по фиксированным значениям стоимости

def extract_price_values(raw_values):
    """Возвращает нормализованный список выбранных цен для фильтра "Цена".

    Простая логика:
        - принимаем список строк/чисел;
        - оставляем только положительные целые значения;
        - убираем дубли, сохраняя исходный порядок.

    Почему здесь возвращаем список строк:
        - во frontend state и в DOM нам удобнее работать со строками;
        - Django безопасно преобразует такие значения при фильтрации DecimalField через __in.
    """
    if not isinstance(raw_values, (list, tuple)):
        return []

    normalized_price_values = []
    seen_price_values = set()

    for raw_value in raw_values:
        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError):
            continue

        if parsed_value <= 0:
            continue

        normalized_value = str(parsed_value)
        if normalized_value in seen_price_values:
            continue

        seen_price_values.add(normalized_value)
        normalized_price_values.append(normalized_value)

    return normalized_price_values


def filter_price(queryset, consultation_type, price_individual_values, price_couple_values):
    """Применяет к QuerySet фильтр "Цена".

    Бизнес-логика здесь такая:
        - если выбран "Индивидуальная", фильтруем только по price_individual;
        - если выбран "Парная", фильтруем только по price_couples;
        - если вид консультации не выбран, разрешаем фильтр по обоим полям и объединяем их через OR.

    Это нужно, чтобы фильтр "Цена" корректно работал и сам по себе, и в связке с фильтром "Вид консультации".
    """
    normalized_individual_values = extract_price_values(price_individual_values)
    normalized_couple_values = extract_price_values(price_couple_values)

    if consultation_type == "individual":
        if not normalized_individual_values:
            return queryset
        return queryset.filter(price_individual__in=normalized_individual_values)

    if consultation_type == "couple":
        if not normalized_couple_values:
            return queryset
        return queryset.filter(price_couples__in=normalized_couple_values)

    if not normalized_individual_values and not normalized_couple_values:
        return queryset

    price_query = Q()
    if normalized_individual_values:
        price_query |= Q(price_individual__in=normalized_individual_values)
    if normalized_couple_values:
        price_query |= Q(price_couples__in=normalized_couple_values)

    return queryset.filter(price_query)


# 7. Фильтр "Опыт": фильтрация по диапазону стажа

def extract_experience_range(raw_experience_min, raw_experience_max, experience_bounds=None):
    """Возвращает безопасный диапазон опыта для фильтра "Опыт".

    Простая логика:
        - берем реальные границы стажа каталога (min/max) из БД или из fallback-констант;
        - пытаемся преобразовать входные значения в целые числа;
        - если значение выходит за границы каталога, прижимаем его к этим границам;
        - если после нормализации выбран весь диапазон целиком, возвращаем (None, None),
          то есть считаем фильтр неактивным.

    Значения None здесь означают:
        - фильтр опыта не выбран;
        - каталог должен показывать специалистов с любым стажем.
    """
    experience_bounds = experience_bounds or {}
    bounds_min = experience_bounds.get("min", DEFAULT_CATALOG_EXPERIENCE_MIN)
    bounds_max = experience_bounds.get("max", DEFAULT_CATALOG_EXPERIENCE_MAX)

    try:
        bounds_min = int(bounds_min)
    except (TypeError, ValueError):
        bounds_min = DEFAULT_CATALOG_EXPERIENCE_MIN

    try:
        bounds_max = int(bounds_max)
    except (TypeError, ValueError):
        bounds_max = DEFAULT_CATALOG_EXPERIENCE_MAX

    if bounds_min > bounds_max:
        bounds_min, bounds_max = bounds_max, bounds_min

    def parse_experience_value(raw_value):
        """Внутренняя вспомогательная функция для обработки одного значения опыта."""
        if raw_value in {"", None}:
            return None

        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError):
            return None

        if parsed_value < bounds_min:
            return bounds_min

        if parsed_value > bounds_max:
            return bounds_max

        return parsed_value

    experience_min = parse_experience_value(raw_experience_min)
    experience_max = parse_experience_value(raw_experience_max)

    if experience_min is not None and experience_max is not None and experience_min > experience_max:
        experience_min, experience_max = experience_max, experience_min

    if experience_min == bounds_min:
        experience_min = None

    if experience_max == bounds_max:
        experience_max = None

    return experience_min, experience_max


def filter_experience(queryset, experience_min, experience_max):
    """Применяет к QuerySet фильтр "Опыт".

    Важно:
        - в модели хранится не сам стаж, а год начала практики;
        - поэтому для фильтрации переводим стаж обратно в диапазон годов.

    Пример:
        - если нужен опыт от 10 лет, значит practice_start_year должен быть не позже current_year - 10;
        - если нужен опыт до 3 лет, значит practice_start_year должен быть не раньше current_year - 3.
    """
    if experience_min is None and experience_max is None:
        return queryset

    current_year = date.today().year

    if experience_min is not None:
        max_start_year = current_year - experience_min
        queryset = queryset.filter(practice_start_year__lte=max_start_year)

    if experience_max is not None:
        min_start_year = current_year - experience_max
        queryset = queryset.filter(practice_start_year__gte=min_start_year)

    return queryset


# ЗАПУСК ФИЛЬТРАЦИИ

def apply_catalog_basic_filters(queryset, filters_state, age_bounds=None, experience_bounds=None):
    """Агрегирует базовые фильтры каталога и применяет их к QuerySet.

    На текущем шаге подключены фильтры:
        - consultation_type.
        - topic_ids.
        - method_ids.
        - gender.
        - price_individual_values / price_couple_values.
        - age_min / age_max.
        - experience_min / experience_max.

    Формат filters_state:
        {
            "consultation_type": "individual" | "couple" | None,
            "topic_ids": ["1", "2"] | [],
            "method_ids": ["3", "7"] | [],
            "gender": "male" | "female" | None,
            "price_individual_values": ["2500", "3500"] | [],
            "price_couple_values": ["3500", "4500"] | [],
            "age_min": 25 | None,
            "age_max": 40 | None,
            "experience_min": 3 | None,
            "experience_max": 15 | None,
        }
    """
    if not isinstance(filters_state, dict):
        filters_state = {}

    consultation_type = extract_consultation_type(
        filters_state.get("consultation_type")
    )
    topic_ids = extract_topic_ids(filters_state.get("topic_ids"))
    method_ids = extract_method_ids(filters_state.get("method_ids"))
    gender = extract_gender(filters_state.get("gender"))
    price_individual_values = extract_price_values(filters_state.get("price_individual_values"))
    price_couple_values = extract_price_values(filters_state.get("price_couple_values"))
    age_min, age_max = extract_age_range(
        filters_state.get("age_min"),
        filters_state.get("age_max"),
        age_bounds=age_bounds,
    )
    experience_min, experience_max = extract_experience_range(
        filters_state.get("experience_min"),
        filters_state.get("experience_max"),
        experience_bounds=experience_bounds,
    )

    queryset = filter_topic_type(queryset, consultation_type)
    queryset = filter_topics(queryset, topic_ids)
    queryset = filter_methods(queryset, method_ids)
    queryset = filter_gender(queryset, gender)
    queryset = filter_price(
        queryset,
        consultation_type,
        price_individual_values,
        price_couple_values,
    )
    queryset = filter_age(queryset, age_min, age_max)
    queryset = filter_experience(queryset, experience_min, experience_max)

    return queryset
