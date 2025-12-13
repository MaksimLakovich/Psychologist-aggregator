# has_preferences = forms.BooleanField(required=False)
# preferred_ps_gender = forms.MultipleChoiceField(choices=GENDER_CHOICES,)
# preferred_ps_age = forms.MultipleChoiceField(choices=AGE_BUCKET_CHOICES,)
# preferred_methods = forms.ModelMultipleChoiceField(queryset=Method.objects.all(),)


# base_queryset()
# get_topic_ids_by_type(topic_type) — вернуть ID тем нужного типа
# filter_by_topic_type(qs, topic_type)
# annotate_topic_matches(qs, topic_ids)
# annotate_method_matches(qs, method_ids)
# apply_gender_filter(qs, genders)
# apply_age_filter(qs, age_buckets)
# finalize_with_score(qs, requested_count, method_count, weights) — аннотирует combined_score и сортирует.


from django.db.models import Count, IntegerField, Q, Value
from django.db.models.functions import Coalesce

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
