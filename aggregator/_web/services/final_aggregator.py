from django.utils.timezone import now

from aggregator._web.services.basic_filter_service import match_psychologists
from aggregator._web.services.scoring import apply_final_ordering
from calendar_engine.application.factories.generate_and_match_factory import \
    build_generate_and_match_use_case
from calendar_engine.application.mappers.preferred_slots_mapper import \
    map_preferred_slots_to_domain
from calendar_engine.constants import DAYS_AHEAD_FOR_SPECIALIST
from calendar_engine.domain.availability.domain_slot_generator import \
    DomainSlotGenerator


class PsychologistAggregatorService:
    """Центральный сервис агрегации:
        - первичная фильтрация (topics, methods, age, gender)
        - финальная фильтрация по selected_slots от пользователя и AvailabilityRule от специалиста
        - финальное ранжирование по коэффициенту совпадения тем и методов (scoring.py)
        - подготовка данных для API / AJAX"""

    def __init__(self, client_profile):
        self.client_profile = client_profile

    def get_aggregated_results(self):
        """Метод ничего не принимает - он работает на основании client_profile, который уже передан в __init__.
        Возвращает dict:
        {
            psychologist_id: {
                "profile": PsychologistProfile,
                "availability": MatchResultDTO | None
            }
        }
        """

        # Шаг 1: Первичная фильтрация (topics, methods, age, gender и считает коэффициенты topic_score, method_score)
        psychologists_qs = match_psychologists(self.client_profile)

        # Получаем выбранные предпочитаемые слоты
        # (preferred_slots нужно адаптировать в доменный формат matcher-а чтоб не было ошибки)
        raw_selected_slots = self.client_profile.preferred_slots
        selected_slots = map_preferred_slots_to_domain(raw_selected_slots)

        # Шаг 2: Если нет предпочтений по времени - просто применяем финальный scoring для итогового ранжирования
        if not self.client_profile.has_time_preferences or not selected_slots:
            ordered_by_scoring_qs = apply_final_ordering(psychologists_qs)

            # Тут превращаем QuerySet в словарь (API удобно работать с profile + availability), где
            # "availability = None" потому что мы ее не считали (if not):
            return {
                ps.id: {
                    "profile": ps,
                    "availability": None,
                }
                for ps in ordered_by_scoring_qs
            }
        # Шаг 3: Генерируем все возможные доменные временные слоты по правилам домена
        # Получаем текущее время в timezone КЛИЕНТА, где astimezone(self.timezone) - это метод, который
        # говорит: "И пересчитай это время для моего часового пояса".
        tz = getattr(self.client_profile.user, "timezone", None)
        current_time = now().astimezone(tz) if tz else now()
        today = current_time.date()

        # Генерируем доменные временные слоты
        generator = DomainSlotGenerator()
        domain_slots = generator.generate_domain_slots(
            date_from=today,
            days_ahead=DAYS_AHEAD_FOR_SPECIALIST,
        )

        # Шаг 4: Финальный агрегированный результат с учетом временными слотами
        aggregated = {}  # Хранит итоговые данные (ТОЛЬКО психологи, которые: прошли проф фильтрацию + проверку слотов
        availability_map = {}  # Временно хранит availability, чтобы потом снова второй раз не вызывать calendar_engine

        # Идем по каждому психологу, который прошел первичную фильтрацию и создаем use-case:
        # - проверяем: есть ли у психолога активный AvailabilityRule
        # - если есть, то запускаем создание use-case для расчета доступных слотов
        for ps in psychologists_qs:
            use_case = build_generate_and_match_use_case(
                psychologist=ps.user,
                selected_slots=selected_slots,
            )

            if not use_case:
                continue  # Выходим: у психолога нет активного AvailabilityRule (например, сейчас не работает)

            # Выполняем расчет слотов: смотрим расписание, применяем исключения, сравниваем с selected_slots
            match_result = use_case.execute(
                domain_slots=domain_slots,
            )

            if not match_result.has_match:
                continue  # Выходим: нет совпадений по слотам (психолог подходит по профилю, но не подходит по времени)

            aggregated[ps.id] = {
                "profile": ps,
                "availability": match_result,
            }
            availability_map[ps.id] = match_result

        # Шаг 5: Итоговое ранжирование полученных результатов с помощью scoring
        if not aggregated:  # Если вообще никто не подошел - это просто безопасный early-return
            return {}

        # ПОЯСНЕНИЕ РЕШЕНИЯ НИЖЕ: dict нельзя просто "отсортировать как queryset из БД", поэтому нужно:
        # а) или переписать apply_final_ordering() в Python-версию. Из-за того что у нас изначально эта функция была
        # написана под QUERYSET
        # б) (КАК У НАС СЕЙЧАС) или оставить apply_final_ordering() как есть и просто применить такой
        # технический прием, чтобы:
        # - снова получить QuerySet
        # - применить существующий SQL-based ранжирование
        # - не писать Python-сортировку вручную
        # где:
        # --- aggregated.keys() - это просто список ID психологов из aggregated, например, dict_keys([12, 7, 31])
        # --- а filter просто возвращает ТОЛЬКО психологов из БД с этими id: 12, 7, 31
        # Очень важно:
        # Django не теряет аннотации topic_score, method_score потому что они уже ранее вычислены в match_psychologists

        ordered_psychologists = apply_final_ordering(
            psychologists_qs.filter(id__in=aggregated.keys())
        )

        return {
            ps.id: {
                "profile": ps,
                "availability": availability_map[ps.id],
            }
            for ps in ordered_psychologists
        }
        # availability_map[ps.id] это match_result (т.е., это MatchResultDTO) и это "дорогое" вычисление, которое
        # мы уже ранее делали и, чтоб не запускать это вычисление второй раз, мы специально его записали/продублировали
        # в availability_map. Потому что знали, что после применения apply_final_ordering() у нас вернется из БД
        # список психологов без MatchResultDTO и чтоб его повторно не считать мы его из ранее записанного
        # справочника availability_map просто подтягиваем по id снова, а не считаем заново!
