from datetime import date, time
from typing import Iterable, List, Set, Tuple

from calendar_engine.domain.availability.dto import SlotDTO
from calendar_engine.domain.matching.base import AbsSlotMatcher
from calendar_engine.domain.matching.dto import MatchResultDTO

# - start_time: пользователь выбирает НАЧАЛО доменного слота.
# - end_time: вычисляется доменной политикой и не участвует в выборе.
# Тип alias (псевдоним):
# Это просто кортеж (day, start_time). Мы дали ему имя, чтобы код читался проще (чище семантически, проще рефакторить)
SlotKey = Tuple[date, time]


class SelectedSlotsMatcher(AbsSlotMatcher):
    """Основной пользовательский matcher, который возвращает пересечение между:
        - доменными слотами, разрешенными индивидуальными правилами доступности специалиста;
        - доменными слотами, явно выбранными пользователем.
    ВАЖНО:
        - matcher НЕ возвращает все выбранные пользователем слоты;
        - matcher возвращает ТОЛЬКО те слоты, которые одновременно:
            1) разрешены специалистом;
            2) были выбраны пользователем."""

    def __init__(self, *, selected_slots: Iterable[SlotKey]) -> None:
        """
        :param selected_slots: Набор доменных временных слотов, выбранных пользователем. Формат: (day, start_time)
        Пример: (date(2026, 1, 22), time(19, 0))
        """
        # Важное действие для повышения быстродействия системы, в котором превращаем список в множество (set):
        # 1) список (list) - это очень долго потому что нужно перебрать все элементы по очереди в списке;
        # 2) А поиск в множестве (set) происходит мгновенно, сколько бы элементов там ни было.
        # Для ядра календаря, где слотов может быть тысячи и тысячи, это критично для скорости.
        self._selected_slots: Set[SlotKey] = set(selected_slots)

        if not self._selected_slots:
            raise ValueError("selected_slots не может быть пустым")

    def match(self, *, allowed_slots: Iterable[SlotDTO]) -> MatchResultDTO:
        """Выполняет matching и возвращает результат. Возвращает пересечение между:
            - доступными слотами специалиста;
            - слотами, выбранными пользователем.

        :param allowed_slots: Доменные слоты специалиста, которые были отфильтрованы по его
        индивидуальным правилам доступности. То есть, по рабочему расписанию с учетом исключений;
        :return: DTO-объект со списком SlotDTO, которые совпали с предпочитаемыми клиентом слотами."""

        matched_slots: List[SlotDTO] = []

        for slot in allowed_slots:
            key: SlotKey = (slot.day, slot.start)
            if key in self._selected_slots:
                matched_slots.append(slot)

        # В самом конце упаковываю все "НАХОДКИ" в итоговый "конверт/коробку" (MatchResultDTO), который дальше готов
        # к транспортировке между слоями системы без использования БД
        return MatchResultDTO(
            matched_slots=matched_slots,
            # applied_criteria - это простая метка, сколько именно слотов пользователь просил проверить.
            # Это может сильно пригодиться для логов и отладки в будущем (чтобы понимать, почему поиск выдал
            # именно такой результат).
            applied_criteria=[
                f"selected_slots:{len(self._selected_slots)}",
            ],
        )
