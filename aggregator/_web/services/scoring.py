from django.db.models import ExpressionWrapper, F, FloatField, Value
from django.db.models.functions import Coalesce


def topic_score(qs, requested_count: int):
    """Метод аннотирует поле topic_score (коэффициент совпадения тем).

    :param qs: Входящие данные с количеством совпадений в темах (matched_topics_count).
    :param requested_count: Количество выбранных клиентом тем.
    :return: Исходящие данные с рассчитанными коэффициентом совпадений на основе количества совпадений."""

    if requested_count and requested_count > 0:
        topic_score_expr = ExpressionWrapper(
            # аннотируем topic_score = matched_topics_count / requested_count
            F("matched_topics_count") * 1.0 / Value(requested_count), output_field=FloatField()
        )
        qs = qs.annotate(
            topic_score=Coalesce(topic_score_expr, Value(0.0, output_field=FloatField()))
        )
    else:
        qs = qs.annotate(
            topic_score=Value(0.0, output_field=FloatField())
        )

    return qs


def method_score(qs, requested_count: int):
    """Метод аннотирует поле method_score (коэффициент совпадения методов).

    :param qs: Входящие данные с количеством совпадений в методах (matched_methods_count).
    :param requested_count: Количество выбранных клиентом методов.
    :return: Исходящие данные с рассчитанными коэффициентом совпадений на основе количества совпадений."""

    if requested_count and requested_count > 0:
        # Рассчитываем method_score = matched_methods_count / requested_count
        method_score_expr = ExpressionWrapper(
            F("matched_methods_count") * 1.0 / Value(requested_count), output_field=FloatField()
        )
        # Аннотируем method_score в qs для каждого психолога
        qs = qs.annotate(
            method_score=Coalesce(method_score_expr, Value(0.0, output_field=FloatField()))
        )
    else:
        qs = qs.annotate(
            method_score=Value(0.0, output_field=FloatField())
        )

    return qs
