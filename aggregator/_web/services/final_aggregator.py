from aggregator._web.services.scoring import apply_final_ordering
from calendar_engine.application.factories.generate_and_match_factory import build_generate_and_match_use_case
from aggregator._web.services.basic_filter_service import match_psychologists
from users.models import PsychologistProfile


class PsychologistAggregatorService:
    """Центральный сервис агрегации:
        - первичная фильтрация (topics, methods, age, gender)
        - финальная фильтрация по selected_slots от пользователя и AvailabilityRule от специалиста
        - финальное ранжирование по коэффициенту совпадения тем и методов (scoring.py)
        - подготовка данных для API / AJAX"""

    def __init__(self, client_profile):
        self.client_profile = client_profile

    def get_aggregated_results(self):
        """Возвращает dict:
        {
            psychologist_id: {
                "profile": PsychologistProfile,
                "availability": MatchResultDTO | None
            }
        }"""

        # Шаг 1: первичная фильтрация (topics, methods, age, gender)
        psychologists_qs = match_psychologists(self.client_profile)

        # Шаг 2: если нет предпочтений по времени - просто применяем финальный scoring для итогового ранжирования
        if not self.client_profile.has_time_preferences:
            ordered_by_scoring_qs = apply_final_ordering(psychologists_qs)

            return {
                ps.id: {
                    "profile": ps,
                    "availability": None,
                }
                for ps in ordered_by_scoring_qs
            }

        # Шаг 3: финальный агрегированный результат с указанными временными слотами
        aggregated = {}
        availability_map = {}

        selected_slots = self.client_profile.preferred_slots

        for ps in psychologists_qs:
            use_case = build_generate_and_match_use_case(
                psychologist=ps.user,
                selected_slots=selected_slots,
            )

            if not use_case:
                continue  # Выходим: у психолога нет активного AvailabilityRule

            match_result = use_case.execute()

            if not match_result.has_match:
                continue  # Выходим: нет совпадений по слотам

            aggregated[ps.id] = {
                "profile": ps,
                "availability": match_result,
            }
            availability_map[ps.id] = match_result

            if not aggregated:
                return {}

        # Шаг 4: Итоговое ранжирование полученных результатов с помощью scoring
        ordered_psychologists = apply_final_ordering(
            PsychologistProfile.objects.filter(id__in=aggregated.keys())
        )

        return {
            ps.id: {
                "profile": ps,
                "availability": availability_map[ps.id],
            }
            for ps in ordered_psychologists
        }
