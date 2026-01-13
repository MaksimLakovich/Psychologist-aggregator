from datetime import date, time
from typing import Iterable, List, Set, Tuple

from calendar_engine.domain.availability.dto import (AvailabilityDayDTO,
                                                     AvailabilityDTO, SlotDTO)
from calendar_engine.domain.matching.base import AbsTimeMatcher
from calendar_engine.domain.matching.dto import MatchResultDTO

# Тип alias (псевдоним): Это просто кортеж (дата, начало, конец). Мы дали ему имя,
# чтобы код читался проще (чище семантически, код легче и проще рефакторить)
SlotKey = Tuple[date, time, time]


class TimeRangeMatcher(AbsTimeMatcher):
    """Это вспомогательный (технический) matcher под будущие админские и сервисные сценарии."""

    def match(self, *, availability: AvailabilityDTO, date_from: date, date_to: date) -> MatchResultDTO:
        """Применяет временные критерии и возвращает результат matching.
        :return: Итоговая отфильтрованная доступность (DTO-объект с доступными слотами)."""
        if date_from > date_to:
            raise ValueError("date_from не может быть позже date_to")

        filtered_days: List[AvailabilityDayDTO] = []

        for day in availability.days:
            if date_from <= day.day <= date_to:
                # День может быть пустым (slots=[]), это допустимо
                filtered_days.append(day)

        filtered_availability = AvailabilityDTO(days=filtered_days)

        return MatchResultDTO(
            availability=filtered_availability,
            applied_criteria=[
                f"date_range:{date_from.isoformat()}–{date_to.isoformat()}",
            ],
        )


class SelectedSlotsMatcher(AbsTimeMatcher):
    """Основной пользовательский matcher - оставляет только те слоты специалиста, которые совпадают с выбранными
    пользователем доменными слотами. Matcher обрабатывает одного специалиста за вызов.
    Используется для:
        - фильтрации специалистов по конкретным выбранным слотам (пользовательский запрос);
        - подготовки данных для агрегатора (поиск специалистов).
    Пример сценария:
        Пользователь выбрал интересующие его слоты -> matching отфильтровал слоты -> aggregator подобрал специалистов,
        у которых есть такие слоты и они свободные."""

    def __init__(self, *, selected_slots: Iterable[SlotKey]) -> None:
        """
        :param selected_slots: Набор доменных слотов, выбранных пользователем. Формат: (day, start_time, end_time)
        """
        # Важное действие для повышения быстродействия системы, в котором превращаем список в множество (set):
        # 1) список (list) - это очень долго потому что нужно перебрать все элементы по очереди в списке;
        # 2) А поиск в множестве (set) происходит мгновенно, сколько бы элементов там ни было.
        # Для ядра календаря, где слотов может быть тысячи и тысячи, это критично для скорости.
        self._selected_slots: Set[SlotKey] = set(selected_slots)

        if not self._selected_slots:
            raise ValueError("selected_slots не может быть пустым")

    def match(
            self,
            *,
            availability: AvailabilityDTO,
            date_from: date | None,
            date_to: date | None,
    ) -> MatchResultDTO:
        """Фильтрует доступность специалиста по выбранным слотам пользователя.
        Для инфо:
            1) текущий метод игнорирует date_from/date_to из абстрактного класса, они присутствуют только для
            совместимости с базовым контрактом AbsTimeMatcher (я просто пока не стал создавать отдельный абстрактный
            класс - пусть это будет "технологическим долгом", а пока решил оставить AbsTimeMatcher).
            2) если ни один слот не совпал - то результат будет пустым (availability.days == []).

        :param availability: Сгенерированная доступность специалиста.
        :param date_from: Игнорируем (присутствуют только для совместимости с базовым контрактом AbsTimeMatcher).
        :param date_to: Игнорируем (присутствуют только для совместимости с базовым контрактом AbsTimeMatcher).
        :return: MatchResultDTO с отфильтрованными слотами."""
        matched_days: List[AvailabilityDayDTO] = []  # Сюда складываю только те дни, в которых найдены совпадения

        for day in availability.days:  # Заходим в каждый день специалиста (например, Понедельник, Вторник...)
            matched_slots: List[SlotDTO] = []

            for slot in day.slots:  # Проверяем каждое свободное окошко в этом дне
                key: SlotKey = (slot.day, slot.start, slot.end)
                if key in self._selected_slots:  # Спрашиваю: "А есть ли этот key в списке тех, что выбрал клиент?"
                    matched_slots.append(slot)  # Если да - добавляю этот слот в список matched_slots

            # Если после проверки всех слотов в дне список matched_slots не пустой (т.е., найдено хотя бы одно
            # совпадение), то создаем новый объект "ДЕНЬ" и помещаю его в итоговый список
            if matched_slots:
                matched_days.append(
                    AvailabilityDayDTO(
                        day=day.day,
                        slots=matched_slots,
                    )
                )

        # В самом конце упаковываю все "НАХОДКИ" в итоговый "конверт/коробку" (MatchResultDTO), который дальше готов
        # к транспортировке между слоями системы без использования БД
        return MatchResultDTO(
            availability=AvailabilityDTO(days=matched_days),
            # applied_criteria - это простая метка, сколько именно слотов пользователь просил проверить.
            # Это может сильно пригодиться для логов и отладки в будущем (чтобы понимать, почему поиск выдал
            # именно такой результат).
            applied_criteria=[
                f"selected_slots:{len(self._selected_slots)}",
            ],
        )
