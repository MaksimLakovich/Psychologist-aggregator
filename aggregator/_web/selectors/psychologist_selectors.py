from django.db.models import Count, IntegerField, Q, Value
from django.db.models.functions import Coalesce

from aggregator._web.services.age_bucket_mapping import AGE_BUCKET_FILTERS
from aggregator._web.services.topic_type_mapping import \
    CLIENT_TO_TOPIC_TYPE_MAP
from users.models import PsychologistProfile


def base_queryset():
    """Метод возвращает базовый QuerySet, содержащий всех активных/верифицированных психологов из базы данных."""

    return (
        PsychologistProfile.objects
        .filter(is_verified=True, user__is_active=True)
        .select_related("user")
        .prefetch_related("methods", "topics")
    )


# def get_topic_ids_by_type(topic_type):
#     """Метод возвращает список id-тем заданного типа (поле type в модели Topic)."""
#
#     if not topic_type:
#         return []
#     return list(
#         Topic.objects.filter(type=topic_type).values_list("id", flat=True)
#     )


def filter_by_topic_type(qs, topic_type):
    """Метод оставляет психологов, у которых в профиле есть хотя бы одна тема (topics) из заданного
    клиентом *Вида консультации* (individual/couple). Это нужно для того, если клиент указал вид консультации,
    но не выбрал ни одной темы из этого вида.

    Для инфо:
        distinct() нужен для удаления дублей строк психологов, которые появляются из-за JOIN'а таблицы topics.
        Например, если у психолога есть 2 темы типа individual (id=3 и id=5), то в join-результате такой психолог
        появится 2 раза, а нам в ответе нужен 1 раз чтоб не выводить его 2 раза клиенту на html-страницах."""

    if not topic_type:
        return qs

    # ВАЖНЫЕ МОМЕНТ: используем явный mapping-слой (адаптер) между полем TYPE в таблице public.users_topic (где
    # указано "Индивидуальная"/"Парная" на русском языке) и полем PREFERRED_TOPIC_TYPE в таблице
    # public.users_clientprofile (где указано "Individual"/"Couple" на английском)
    mapped_topic_type = CLIENT_TO_TOPIC_TYPE_MAP.get(topic_type)

    return qs.filter(topics__type=mapped_topic_type).distinct()


def annotate_type_topic_count(qs, topic_type):
    """Метод аннотирует поле type_topics_count. Данные о том сколько у каждого психолога указано в его профиле тем
    из указанного клиентом *Вида консультации*: individual / couple (полезно когда requested_topics пуст).

    Для инфо:
        1) annotate() добавляет к каждому объекту из QuerySet дополнительное вычисляемое поле (type_topics_count),
        полученное с помощью агрегации/выражения.
        2) filter=Q(topics__type=topic_type) - это фильтр прямо внутри Count (новая, удобная возможность Django).
        Он говорит: считай только те связанные Topic, у которых type == topic_type.
        Это позволяет посчитать, например, сколько у психолога "Индивидуальных" тем, не выполняя отдельный
        фильтр перед всем QuerySet.
        3) distinct=True - необходим, чтобы исключить дубли при джойнах (иногда при сложных связях одна и та же
        тема может попасть в подсчет несколько раз из-за дополнительных джойнов). distinct гарантирует,
        что считаем уникальные связанные темы."""

    if not topic_type:
        return qs.annotate(
            type_topics_count=Value(0, output_field=IntegerField())
        )
    return qs.annotate(
        type_topics_count=Coalesce(
            Count("topics", filter=Q(topics__type=topic_type), distinct=True),
            Value(0),
        )
    )


def annotate_topic_matches(qs, requested_topic_ids):
    """Метод аннотирует поле matched_topics_count, где подсчитывает количество совпадающих тем из
    профиля психолога (topics) с темами из профиля клиента (requested_topics).

    Для инфо:
        1) annotate() добавляет к каждому объекту из QuerySet дополнительное вычисляемое поле (matched_topics_count),
        полученное с помощью агрегации/выражения.
        2) filter=Q(topics__in=requested_topic_ids) - это фильтр прямо внутри Count (удобная возможность Django).
        Он говорит: считай только те связанные Topic, которые есть в requested_topic_ids.
        Это позволяет посчитать, сколько у психолога есть интересующих клиента тем, не выполняя отдельный
        фильтр перед всем QuerySet.
        3) distinct=True - необходим, чтобы исключить дубли при джойнах (иногда при сложных связях одна и та же
        тема может попасть в подсчет несколько раз из-за дополнительных джойнов). distinct гарантирует,
        что считаем уникальные связанные темы."""

    if not requested_topic_ids:
        # гарантируем наличие поля, равного 0 (если у психолога нет тем то запрос вернет null, а мы его заменим на 0)
        return qs.annotate(
            matched_topics_count=Value(0, output_field=IntegerField())
        )
    return qs.annotate(
        matched_topics_count=Coalesce(
            Count("topics", filter=Q(topics__in=requested_topic_ids), distinct=True),
            Value(0)
        )
    )


def filter_by_gender(qs, client_profile):
    """Метод с жесткой фильтрацией по полу психолога (мужчина/женщина)."""

    if not client_profile.preferred_ps_gender:
        return qs

    qs = qs.filter(gender__in=client_profile.preferred_ps_gender)

    return qs


def filter_by_age(qs, client_profile):
    """Метод с жесткой фильтрацией по возрасту психолога.
    Используется AGE_BUCKET_FILTERS - явный mapping-слой (адаптер) между полем BUCKET и тем,
    какие значения (числа) в него входят. Например, в "25-35" значения от >=25, но меньше 35.

    Пояснение финальной строки "age_q = age_q | bucket_q" шаг за шагом:

    1) Представим, что первый bucket который выбрал клиент - ("25-35"), тогда:
        bucket_q = Q(age__gte=25, age__lt=35)
        age_q = Q() | bucket_q
            то есть:
                берем пустой изначальный Q() и добавляем "условие OR (или)" - получаем результат с ОДНИМ условием:
                    age_q == Q(age__gte=25, age__lt=35)

    2) Представим, что второй bucket который выбрал клиент - ("45-55"), тогда:
        bucket_q = Q(age__gte=45, age__lt=55)
        age_q = (
            Q(age__gte=25, age__lt=35)
            |
            Q(age__gte=45, age__lt=55)
        )
            то есть:
                берем наш Q() с первым условием и добавляем "условие OR (или)" - получаем результат с ДВУМЯ условиями.

    3) Получаем SQL-логику:
        (age >= 25 AND age < 35)
        OR
        (age >= 45 AND age < 55)"""

    selected_buckets = client_profile.preferred_ps_age

    if not selected_buckets:
        return qs

    # Q() - это объект Django для построения сложных условий WHERE. Пустой Q() = “ничего не фильтруем”, то есть
    # создаю пустое условие, в которое буду постепенно добавлять правила потом.
    age_q = Q()

    for bucket in selected_buckets:
        rule = AGE_BUCKET_FILTERS.get(bucket)  # Берем описание диапазона для каждого bucket-а.
        if not rule:
            continue

        # Создаем условие для ОДНОГО bucket:
        # 1) bucket_q - условия внутри одного диапазона
        # 2) age_q - объединяет все диапазоны

        bucket_q = Q()
        if "gte" in rule:  # gte - больше и равно
            bucket_q &= Q(user__age__gte=rule["gte"])
        if "lt" in rule:  # lt - меньше
            bucket_q &= Q(user__age__lt=rule["lt"])

        age_q = age_q | bucket_q  # Детальное пояснение в docstrings

    return qs.filter(age_q)


def annotate_method_matches(qs, preferred_method_ids):
    """Метод аннотирует поле matched_methods_count, где подсчитывает количество совпадающих методов из
    профиля психолога (methods) с методами из профиля клиента (preferred_methods).

    Для инфо:
        1) annotate() добавляет к каждому объекту из QuerySet дополнительное вычисляемое поле (matched_methods_count),
        полученное с помощью агрегации/выражения.
        2) filter=Q(methods__in=preferred_method_ids) - это фильтр прямо внутри Count (удобная возможность Django).
        Он говорит: считай только те связанные Methods, которые есть в preferred_methods.
        Это позволяет посчитать, сколько у психолога есть интересующих клиента методов, не выполняя отдельный
        фильтр перед всем QuerySet.
        3) distinct=True - необходим, чтобы исключить дубли при джойнах (иногда при сложных связях один и тот же
        метод может попасть в подсчет несколько раз из-за дополнительных джойнов). distinct гарантирует,
        что считаем уникальные связанные методы."""

    if not preferred_method_ids:
        # гарантируем наличие поля, равного 0 (если у психолога нет методов то вернется null, а мы его заменим на 0)
        return qs.annotate(
            matched_methods_count=Value(0, output_field=IntegerField())
        )
    return qs.annotate(
        matched_methods_count=Coalesce(
            Count("methods", filter=Q(methods__in=preferred_method_ids), distinct=True),
            Value(0)
        )
    )
