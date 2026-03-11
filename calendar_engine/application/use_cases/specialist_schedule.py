from datetime import datetime, timedelta
from typing import Dict, List

from calendar_engine.application.use_cases.base import AbsUseCase
from calendar_engine.domain.availability.domain_slot_generator import \
    DomainSlotGenerator
from calendar_engine.domain.availability.dto import SlotDTO
from calendar_engine.domain.availability.get_user_slots import \
    AvailabilitySlotFilter
from calendar_engine.services import normalize_range


class GenerateSpecialistScheduleUseCase(AbsUseCase):
    """Use-case получения актуального расписания специалиста (в TZ СПЕЦИАЛИСТА).
    Ответственность:
        - сгенерировать доменные слоты;
        - отфильтровать их по AvailabilityRule / AvailabilityException / Booking;
        - вернуть список доступных SlotDTO."""

    def __init__(
        self,
        *,
        slot_generator: DomainSlotGenerator,
        slot_filter: AvailabilitySlotFilter,
        date_from,
        days_ahead: int,
        current_datetime,
        session_duration_minutes: int,
        break_between_sessions_minutes: int,
        override_session_duration_minutes_by_day: Dict,
        override_break_between_sessions_minutes_by_day: Dict,
        minimum_booking_notice_hours: int,
        override_minimum_booking_notice_hours_by_day: Dict,
        busy_intervals: List[tuple[datetime, datetime]],
    ) -> None:
        """
        :param slot_generator: Генерирует все возможные доменные временные слоты по правилам домена.
        :param slot_filter: Фильтр всех возможных доменных слотов по индивидуальным правилам доступности специалиста.
        :param date_from: Текущая дата в timezone специалиста.
        :param days_ahead: Количество дней на которое рассчитывается расписание специалиста.
        :param current_datetime: Текущее время в timezone специалиста.
        :param session_duration_minutes: Базовая продолжительность сессии для текущего consultation_type.
        :param break_between_sessions_minutes: Базовый перерыв между сессиями специалиста.
        :param override_session_duration_minutes_by_day: Словарь вида {date: minutes}, который позволяет на
            отдельные даты временно менять duration для текущего consultation_type.
        :param override_break_between_sessions_minutes_by_day: Словарь вида {date: minutes}, который позволяет на
            отдельные даты временно менять перерыв между сессиями.
        :param minimum_booking_notice_hours: Базовое минимальное количество часов до старта слота для записи.
        :param override_minimum_booking_notice_hours_by_day: Словарь вида {date: hours}, который позволяет на
            отдельные даты переопределить базовый minimum notice.
        :param busy_intervals: Список уже занятых интервалов специалиста в timezone специалиста.
            Каждый интервал хранится как (busy_start, busy_end), где busy_end уже учитывает break_between_sessions
            для ранее созданных встреч и нужен только для блокировки последующих доменных стартов.
        """
        self._slot_generator = slot_generator
        self._slot_filter = slot_filter
        self._date_from = date_from
        self._days_ahead = days_ahead
        self._current_datetime = current_datetime
        self._session_duration_minutes = session_duration_minutes
        self._break_between_sessions_minutes = break_between_sessions_minutes
        self._override_session_duration_minutes_by_day = override_session_duration_minutes_by_day
        self._override_break_between_sessions_minutes_by_day = override_break_between_sessions_minutes_by_day
        self._minimum_booking_notice_hours = minimum_booking_notice_hours
        self._override_minimum_booking_notice_hours_by_day = override_minimum_booking_notice_hours_by_day
        self._busy_intervals = busy_intervals

    def _build_slot_datetimes(self, *, slot: SlotDTO, session_duration_minutes: int) -> tuple[datetime, datetime]:
        """Строит реальные aware datetime для кандидата на запись из доменного SlotDTO.

        Важно:
            - SlotDTO приходит из доменной политики и всегда отражает только старт доменного слота;
            - фактическое окончание потенциальной сессии определяется уже рабочими правилами специалиста
              (session_duration_*), а не самой доменной сеткой.
        """
        slot_start_datetime = datetime.combine(
            slot.day,
            slot.start,
            tzinfo=self._current_datetime.tzinfo,
        )
        slot_end_datetime = slot_start_datetime + timedelta(minutes=session_duration_minutes)

        # ВЫПОЛНЯЕМ НОРМАЛИЗАЦИЮ:
        # т.е., нужно сравнивать datetime, а не time, чтобы корректно учитывать интервалы, пересекающие границу суток.
        # Для этого используем сервисную вспомогательную функцию normalize_range().
        # Здесь нормализуется сам интервал будущей сессии:
        # - старт доменного слота
        # - чистый конец сессии по session_duration
        normalized_start_datetime, normalized_end_datetime = normalize_range(
            slot.day,
            slot_start_datetime.timetz().replace(tzinfo=None),
            slot_end_datetime.timetz().replace(tzinfo=None),
        )

        return (
            normalized_start_datetime.replace(tzinfo=self._current_datetime.tzinfo),
            normalized_end_datetime.replace(tzinfo=self._current_datetime.tzinfo),
        )

    def _slot_fits_working_windows(
        self,
        *,
        slot: SlotDTO,
        session_duration_minutes: int,
    ) -> bool:
        """Проверяет, помещается ли реальная длительность сессии в рабочие окна специалиста.

        Ключевая логика:
            - доменная сетка стартов остается общей для всех специалистов;
            - но сам факт доступности старта (слота) зависит от того, помещается ли реальная сессия специалиста
              в его рабочее окно.

        Например:
            - если доменный слот стартует в 11:00;
            - а рабочее окно специалиста заканчивается в 12:00;
            - и для парной сессии duration = 120 минут;
            - значит такой старт (слот) показывать нельзя, даже если сама доменная сетка его содержит.
        """
        # 1) Превращаем абстрактный доменный старт в реальный интервал будущей сессии специалиста.
        # Например:
        #   - доменный слот = "23:00";
        #   - реальная длительность сессии = 120 минут;
        #   - значит фактически это уже интервал "23:00 -> 01:00 следующего дня"
        slot_start_datetime, slot_end_datetime = self._build_slot_datetimes(
            slot=slot,
            session_duration_minutes=session_duration_minutes,
        )

        # 2) Берем рабочие окна специалиста именно для этого календарного дня.
        # На этом этапе доменная сетка уже отфильтрована под AvailabilityRule / AvailabilityException,
        # но теперь нужно понять более точную вещь:
        #   - помещается ли полная длительность конкретной сессии в одно из разрешенных окон дня
        for window_start, window_end in self._slot_filter.get_user_time_windows(slot.day):
            # ВЫПОЛНЯЕМ НОРМАЛИЗАЦИЮ:
            # т.е., чтобы корректно учитывать интервалы, пересекающие границу суток - normalize_range().
            # Здесь повторно нормализуется рабочие окна специалиста (рабочее окно тоже может пересекать полночь)
            normalized_window_start_datetime, normalized_window_end_datetime = normalize_range(
                slot.day,
                window_start,
                window_end,
            )
            window_start_datetime = normalized_window_start_datetime.replace(
                tzinfo=self._current_datetime.tzinfo,
            )
            window_end_datetime = normalized_window_end_datetime.replace(
                tzinfo=self._current_datetime.tzinfo,
            )

            # 3) Слот считаем допустимым только если будущая сессия целиком помещается в рабочее окно.
            # Пример:
            #   - окно специалиста = "09:00-12:00";
            #   - слот стартует в "11:00";
            #   - длительность = 50 минут;
            #   - значит слот еще допустим.
            # Но если длительность = 120 минут, то показывать такой старт уже нельзя
            if (
                slot_start_datetime >= window_start_datetime
                and slot_end_datetime <= window_end_datetime
            ):
                return True

        return False

    def _slot_conflicts_with_busy_intervals(
        self,
        *,
        slot: SlotDTO,
        session_duration_minutes: int,
        break_between_sessions_minutes: int,
    ) -> bool:
        """Проверяет, конфликтует ли потенциальная запись с уже занятыми интервалами специалиста.

        Здесь учитываем именно busy-интервал кандидата:
            - старт доменного слота;
            - чистую продолжительность сессии;
            - и обязательный перерыв после нее.

        Это позволяет:
            - не менять доменную сетку стартов (слотов);
            - но корректно скрывать следующие доменные старты, если предыдущая встреча + break их перекрывают.
        """
        # 1) Строим интервал самой потенциальной сессии без перерыва
        candidate_start_datetime, candidate_end_datetime = self._build_slot_datetimes(
            slot=slot,
            session_duration_minutes=session_duration_minutes,
        )

        # 2) Поверх чистой длительности сессии добавляем обязательный перерыв специалиста.
        # Именно этот "расширенный" интервал и должен блокировать последующие доменные старты.
        candidate_busy_end_datetime = candidate_end_datetime + timedelta(
            minutes=break_between_sessions_minutes
        )
        # ВЫПОЛНЯЕМ НОРМАЛИЗАЦИЮ:
        # т.е., чтобы корректно учитывать интервалы, пересекающие границу суток - normalize_range().
        # После добавления break это уже новый интервал, и его нужно нормализовать отдельно
        normalized_candidate_start_datetime, normalized_candidate_busy_end_datetime = normalize_range(
            candidate_start_datetime.date(),
            candidate_start_datetime.timetz().replace(tzinfo=None),
            candidate_busy_end_datetime.timetz().replace(tzinfo=None),
        )

        candidate_start_datetime = normalized_candidate_start_datetime.replace(
            tzinfo=self._current_datetime.tzinfo,
        )
        candidate_busy_end_datetime = normalized_candidate_busy_end_datetime.replace(
            tzinfo=self._current_datetime.tzinfo,
        )

        # 3) Сравниваем кандидата со всеми уже существующими busy intervals специалиста.
        # Если новый старт пересекается хотя бы с одним из них, такой слот уже нельзя показывать как доступный
        for busy_start_datetime, busy_end_datetime in self._busy_intervals:
            # ВЫПОЛНЯЕМ НОРМАЛИЗАЦИЮ:
            # т.е., чтобы корректно учитывать интервалы, пересекающие границу суток - normalize_range().
            # Отдельно нормализуются и уже существующие busy_intervals из БД, так как тоже могут пересекать полночь
            normalized_busy_start_datetime, normalized_busy_end_datetime = normalize_range(
                busy_start_datetime.date(),
                busy_start_datetime.timetz().replace(tzinfo=None),
                busy_end_datetime.timetz().replace(tzinfo=None),
            )
            busy_start_datetime = normalized_busy_start_datetime.replace(
                tzinfo=self._current_datetime.tzinfo,
            )
            busy_end_datetime = normalized_busy_end_datetime.replace(
                tzinfo=self._current_datetime.tzinfo,
            )

            if (
                candidate_start_datetime < busy_end_datetime
                and candidate_busy_end_datetime > busy_start_datetime
            ):
                return True

        return False

    def execute(self) -> List[SlotDTO]:
        """Генерируем все возможные доменные временные слоты и выполняем бизнес-операцию
        получения расписания специалиста с учетом рабочего расписания и действующих исключений в нем.

        :return: Список доступных слотов специалиста (расписание специалиста).
        """
        # 1) Генерируем полную доменную сетку стартов на ближайшие дни.
        # Это именно общие слоты домена по DomainTimePolicy, а не персональное расписание специалиста
        domain_slots = self._slot_generator.generate_domain_slots(
            date_from=self._date_from,
            days_ahead=self._days_ahead,
        )

        # 2) Из общей доменной сетки убираем все старты (слоты), которые вообще не попадают в рабочие окна специалиста
        # по AvailabilityRule / AvailabilityException
        allowed_slots = self._slot_filter.filter_user_slots(
            domain_slots=domain_slots
        )

        # После того как получили все допустимые слоты специалиста по рабочему расписанию и исключениям,
        # дополнительно отсекаем слишком "близкие" к текущему моменту слоты.
        # Бизнес-смысл:
        #   - если сейчас 10:57, а minimum_booking_notice_hours = 1 час,
        #   - то слот на 11:00 не должен показываться клиенту как доступный для записи.
        filtered_by_notice: List[SlotDTO] = []

        for slot in allowed_slots:
            # 3) Для каждого конкретного дня определяем "эффективные" параметры специалиста.
            # Это значит:
            #   - если на день есть override в AvailabilityException, берем его;
            #   - если нет, берем базовые настройки из AvailabilityRule.
            effective_session_duration_minutes = self._override_session_duration_minutes_by_day.get(
                slot.day,
                self._session_duration_minutes,
            )
            effective_break_between_sessions_minutes = self._override_break_between_sessions_minutes_by_day.get(
                slot.day,
                self._break_between_sessions_minutes,
            )
            effective_minimum_booking_notice_hours = self._override_minimum_booking_notice_hours_by_day.get(
                slot.day,
                self._minimum_booking_notice_hours,
            )

            earliest_allowed_start = self._current_datetime + timedelta(
                hours=effective_minimum_booking_notice_hours
            )

            # 4) Переводим доменный старт в реальный datetime специалиста,
            # чтобы понять не слишком ли "близко" этот слот к текущему моменту.
            slot_start_datetime = datetime.combine(
                slot.day,
                slot.start,
                tzinfo=self._current_datetime.tzinfo,
            )

            # 5) Если специалист указал minimum notice, то слишком близкие слоты клиенту не показываем.
            # Пример:
            #   - сейчас 10:57;
            #   - minimum notice = 2 часа;
            #   - значит старт на 11:00 или 12:00 уже нельзя показывать.
            if slot_start_datetime < earliest_allowed_start:
                continue

            # 6) Даже если доменный старт попадает в рабочее окно дня, нужно дополнительно проверить,
            # что полная сессия выбранного типа действительно помещается в рабочий интервал специалиста.
            if not self._slot_fits_working_windows(
                slot=slot,
                session_duration_minutes=effective_session_duration_minutes,
            ):
                continue

            # 7) И в конце проверяем пересечение с уже существующими встречами специалиста,
            # включая обязательный перерыв после них. Если есть пересечение - такой старт скрываем.
            if self._slot_conflicts_with_busy_intervals(
                slot=slot,
                session_duration_minutes=effective_session_duration_minutes,
                break_between_sessions_minutes=effective_break_between_sessions_minutes,
            ):
                continue

            filtered_by_notice.append(slot)

        return filtered_by_notice
