from django.db.models import F

from aggregator._web.selectors.psychologist_selectors import (
    annotate_method_matches, annotate_topic_matches, annotate_type_topic_count,
    base_queryset, filter_by_age, filter_by_gender, filter_by_topic_type)
from aggregator._web.services.scoring import method_score, topic_score
from aggregator._web.services.topic_type_mapping import \
    CLIENT_TO_TOPIC_TYPE_MAP


def match_psychologists(client_profile):
    """Метод возвращает итоговый QuerySet, содержащий психологов отсортированных по:
        - коэффициенту совпадения тем (requested_topics);
        - полу психолога (preferred_ps_gender);
        - возрасту психолога (preferred_ps_age);
        - коэффициенту совпадения методов (preferred_methods)."""

    qs = base_queryset()

    preferred_type = client_profile.preferred_topic_type  # "individual" / "couple"

    # ВАЖНЫЕ МОМЕНТ: используем явный mapping-слой (адаптер) между полем TYPE в таблице public.users_topic (где
    # указано "Индивидуальная"/"Парная" на русском языке) и полем PREFERRED_TOPIC_TYPE в таблице
    # public.users_clientprofile (где указано "Individual"/"Couple" на английском)
    mapped_topic_type = CLIENT_TO_TOPIC_TYPE_MAP.get(preferred_type)
    requested_topics_qs = client_profile.requested_topics.filter(type=mapped_topic_type)
    requested_topics_ids = list(requested_topics_qs.values_list("id", flat=True))

    # Шаг 1: Если клиент указал хотя бы одну конкретную тему, то:
    if requested_topics_ids:
        # 1) сначала ограничим психологов, у которых есть хотя бы одна тема из указанного типа (individual"/"couple)
        qs = filter_by_topic_type(qs, preferred_type)
        # 2) аннотируем matched_topics_count (сколько тем из requested_topics_ids есть у психолога)
        qs = annotate_topic_matches(qs, requested_topics_ids)
        # 3) оставим только тех, у кого matched_topics_count > 0
        qs = qs.filter(matched_topics_count__gt=0)
        # 4) аннотируем topic_score = matched_topics_count / requested_count
        qs = topic_score(qs, requested_count=len(requested_topics_ids))
        # 5) сортируем по score desc (дальше можно расширять когда реализуем reviews с рейтингами или subscription)
        qs = qs.order_by(F("topic_score").desc(nulls_last=True))

    # Шаг 2: Если клиент не указал ни одной темы, то берем всех психологов, у которых есть любые темы из этого типа
    else:
        qs = filter_by_topic_type(qs, preferred_type)
        # аннотируем сколько у них тем этого типа - для сортировки/информации
        qs = annotate_type_topic_count(qs, preferred_type)
        qs = qs.order_by(F("type_topics_count").desc(nulls_last=True))

        # Для унификации структуры добавим matched_topics_count=type_topics_count и topic_score=0
        qs = qs.annotate(matched_topics_count=F("type_topics_count"))
        qs = topic_score(qs, requested_count=0)

    # Шаг 3: Если клиент указал, что нет дополнительных предпочтений/пожеланий
    if not client_profile.has_preferences:
        return qs

    # Шаг 4: Если клиент указал, что есть доп пожелания - фильтруем по полу, возраста и методам
    qs = filter_by_gender(qs, client_profile)
    qs = filter_by_age(qs, client_profile)

    # Методы
    preferred_methods_qs = client_profile.preferred_methods.all()
    preferred_method_ids = list(preferred_methods_qs.values_list("id", flat=True))
    if preferred_method_ids:
        # 1) аннотируем matched_methods_count (сколько методов из preferred_method_ids есть у психолога)
        qs = annotate_method_matches(qs, preferred_method_ids)
        # 2) аннотируем method_score = matched_methods_count / requested_count
        qs = method_score(qs, requested_count=len(preferred_method_ids))
        # 3) сортируем по score desc (дальше можно расширять когда реализуем reviews с рейтингами или subscription)
        qs = qs.order_by(F("method_score").desc(nulls_last=True))

    # Добавлен ВРЕМЕННЫЙ DEBUG
    print("preferred_type:", preferred_type)
    print("requested_topics_ids:", requested_topics_ids)
    print("preferred_method_ids:", preferred_method_ids)
    print("base qs count:", base_queryset().count())
    print("final qs count:", qs.count())

    return qs
