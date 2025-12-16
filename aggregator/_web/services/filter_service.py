from django.db.models import F, FloatField, IntegerField, Value

from aggregator._web.selectors.psychologist_selectors import (
    annotate_method_matches, annotate_topic_matches, annotate_type_topic_count,
    base_queryset, filter_by_age, filter_by_gender, filter_by_topic_type)
from aggregator._web.services.scoring import (apply_final_ordering,
                                              method_score, topic_score)
from aggregator._web.services.topic_type_mapping import \
    CLIENT_TO_TOPIC_TYPE_MAP


def match_psychologists(client_profile):
    """Метод возвращает итоговый QuerySet, содержащий психологов отсортированных по:
        - коэффициенту совпадения тем (requested_topics);
        - полу психолога (preferred_ps_gender);
        - возрасту психолога (preferred_ps_age);
        - коэффициенту совпадения методов (preferred_methods)."""

    qs = base_queryset().annotate(
        matched_methods_count=Value(0, output_field=IntegerField()),
        method_score=Value(0.0, output_field=FloatField()),
    )

    preferred_type = client_profile.preferred_topic_type
    # ВАЖНЫЕ МОМЕНТ: используем явный mapping-слой (адаптер) между полем TYPE в таблице public.users_topic (где
    # указано "Индивидуальная"/"Парная" на русском языке) и полем PREFERRED_TOPIC_TYPE в таблице
    # public.users_clientprofile (где указано "Individual"/"Couple" на английском)
    mapped_topic_type = CLIENT_TO_TOPIC_TYPE_MAP.get(preferred_type)
    requested_topics_qs = client_profile.requested_topics.filter(type=mapped_topic_type)
    requested_topics_ids = list(requested_topics_qs.values_list("id", flat=True))

    # --- TOPICS ---
    # Если клиент указал хотя бы одну конкретную тему, то:
    if requested_topics_ids:
        # 1) сначала ограничим психологов, у которых есть хотя бы одна тема из указанного типа (individual"/"couple)
        qs = filter_by_topic_type(qs, preferred_type)
        # 2) аннотируем matched_topics_count (сколько тем из requested_topics_ids есть у психолога)
        qs = annotate_topic_matches(qs, requested_topics_ids)
        # 3) оставим только тех, у кого matched_topics_count > 0
        qs = qs.filter(matched_topics_count__gt=0)
        # 4) аннотируем topic_score = matched_topics_count / requested_count
        qs = topic_score(qs, requested_count=len(requested_topics_ids))

    # Если клиент не указал ни одной темы, то берем всех психологов, у которых есть любые темы из этого типа
    else:
        # 1) сначала ограничим психологов, у которых есть хотя бы одна тема из указанного типа (individual"/"couple)
        qs = filter_by_topic_type(qs, preferred_type)
        # 2) аннотируем сколько у них тем этого типа - для сортировки/информации
        qs = annotate_type_topic_count(qs, preferred_type)
        # 3) для унификации структуры добавим matched_topics_count=type_topics_count и topic_score=0
        qs = qs.annotate(matched_topics_count=F("type_topics_count"))
        qs = topic_score(qs, requested_count=0)

    # --- PREFS ---
    # 1) Если клиент указал, что нет дополнительных предпочтений/пожеланий
    if not client_profile.has_preferences:
        qs = apply_final_ordering(qs)

        return qs

    # 2) Если клиент указал, что есть доп пожелания - фильтруем по полу, возрасту и методам
    qs = filter_by_gender(qs, client_profile)
    qs = filter_by_age(qs, client_profile)

    # 3) Методы
    preferred_methods_qs = client_profile.preferred_methods
    preferred_method_ids = list(preferred_methods_qs.values_list("id", flat=True))

    if preferred_method_ids:
        # 1) аннотируем matched_methods_count (сколько методов из preferred_method_ids есть у психолога)
        qs = annotate_method_matches(qs, preferred_method_ids)
        # 2) аннотируем method_score = matched_methods_count / requested_count
        qs = method_score(qs, requested_count=len(preferred_method_ids))

    qs = apply_final_ordering(qs)

    return qs
