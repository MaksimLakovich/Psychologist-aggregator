from django.db.models import F

from aggregator._web.selectors.psychologist_selectors import (
    annotate_topic_matches, annotate_type_topic_count, base_queryset,
    filter_by_topic_type)
from aggregator._web.services.scoring import topic_score
from aggregator._web.services.topic_type_mapping import \
    CLIENT_TO_TOPIC_TYPE_MAP


def match_psychologists_by_topics(client_profile):
    """Метод возвращает итоговый QuerySet, содержащий психологов отсортированных по коэффициенту совпадения тем."""

    qs = base_queryset()

    preferred_type = client_profile.preferred_topic_type  # "individual" / "couple"
    # # ПОКА НЕ ИСПОЛЬЗУЕМ!!! Получим ids всех тем данного типа (может пригодиться позже)
    # type_topic_ids = get_topic_ids_by_type(preferred_type)

    # ВАЖНЫЕ МОМЕНТ: используем явный mapping-слой (адаптер) между полем TYPE в таблице public.users_topic (где
    # указано "Индивидуальная"/"Парная" на русском языке) и полем PREFERRED_TOPIC_TYPE в таблице
    # public.users_clientprofile (где указано "Individual"/"Couple" на английском)
    mapped_topic_type = CLIENT_TO_TOPIC_TYPE_MAP.get(preferred_type)
    requested_topics_qs = client_profile.requested_topics.filter(type=mapped_topic_type)

    requested_ids = list(requested_topics_qs.values_list("id", flat=True))

    # Шаг 1: если клиент указал хотя бы одну конкретную тему, то:
    if requested_ids:
        # 1) сначала ограничим психологов, у которых есть хотя бы одна тема из указанного типа (individual"/"couple)
        qs = filter_by_topic_type(qs, preferred_type)
        # 2) аннотируем matched_topics_count (сколько тем из requested_ids есть у психолога)
        qs = annotate_topic_matches(qs, requested_ids)
        # 3) оставим только тех, у кого matched_topics_count > 0
        qs = qs.filter(matched_topics_count__gt=0)
        # 4) аннотируем topic_score = matched_topics_count / requested_count
        qs = topic_score(qs, requested_count=len(requested_ids))
        # 5) сортируем по score desc (дальше можно расширять когда реализуем reviews с рейтингами или subscription)
        qs = qs.order_by(F("topic_score").desc(nulls_last=True))

    # Шаг 2: если клиент не указал ни одной темы, то берем всех психологов, у которых есть любые темы из этого типа
    else:
        qs = filter_by_topic_type(qs, preferred_type)
        # аннотируем сколько у них тем этого типа - для сортировки/информации
        qs = annotate_type_topic_count(qs, preferred_type)
        qs = qs.order_by(F("type_topics_count").desc(nulls_last=True))

        # Для унификации структуры добавим matched_topics_count=type_topics_count и topic_score=0
        qs = qs.annotate(matched_topics_count=F("type_topics_count"))
        qs = topic_score(qs, requested_count=0)

    # Добавлен ВРЕМЕННЫЙ DEBUG
    print("preferred_type:", preferred_type)
    print("requested_ids:", requested_ids)
    print("base qs count:", base_queryset().count())
    print("final qs count:", qs.count())

    return qs


# def filter_by_preferences(client_profile):
#     """Возвращает QuerySet психологов, отфильтрованный с учетом логики has_preference.
#
#     Логика:
#     - если "has_preference = False":
#         фильтр по:
#             preferred_topic_type
#             requested_topics
#     - если "has_preference = True":
#         фильтр по:
#             preferred_ps_gender
#             preferred_ps_age_bucket
#             preferred_methods
#     """
#
#     qs = PsychologistProfile.objects.select_related("user").prefetch_related(
#         "methods",
#         "topics"
#     ).all()
#
#     # 1. Всегда фильтруем по requested_topics
#     requested_topics = client_profile.requested_topics.values_list("id", flat=True)
#
#     if requested_topics:
#         qs = qs.filter(
#             topics__in=requested_topics
#         )
#     else:
#         # если клиент не выбрал ни одной темы — возвращаем пустой QuerySet
#         # иначе фильтрация будет слишком широкой
#         return PsychologistProfile.objects.none()
#
#     # --------------------------------------
#     # 2. Если клиент НЕ хочет применять предпочтения
#     # --------------------------------------
#     if not client_profile.has_preference:
#         return qs.distinct()
#
#     # --------------------------------------
#     # 3. Клиент хочет учитывать предпочтения
#     #    Фильтрация по preferred_methods
#     # --------------------------------------
#     preferred_methods = client_profile.preferred_methods.values_list("id", flat=True)
#
#     if preferred_methods:
#         qs = qs.filter(
#             methods__in=preferred_methods
#         )
#
#     # --------------------------------------
#     # 4. Фильтрация по полу психолога
#     # --------------------------------------
#     ps_genders = client_profile.preferred_ps_gender or []
#
#     if ps_genders:
#         qs = qs.filter(
#             gender__in=ps_genders
#         )
#
#     # --------------------------------------
#     # 5. Фильтрация по возрасту психолога
#     #    (age_bucket находится в AppUser.age)
#     # --------------------------------------
#     ps_age_buckets = client_profile.preferred_ps_age or []
#
#     if ps_age_buckets:
#         qs = qs.filter(
#             user__age_bucket__in=ps_age_buckets
#         )
#
#     # --------------------------------------
#     # 6. Убираем дубликаты, т.к. было M2M фильтрование
#     # --------------------------------------
#     return qs.distinct()
