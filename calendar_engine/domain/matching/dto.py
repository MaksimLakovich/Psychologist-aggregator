from dataclasses import dataclass
from typing import List

from calendar_engine.domain.availability.dto import AvailabilityDTO


@dataclass(frozen=True)
class MatchResultDTO:
    """DTO результата domain-matching.
        - frozen=True делает объект "замороженным/неизменяемым" - после создания нельзя поменять start/duration.
        - Цель: DTO-объект, предназначен только для транспортировки данных между слоями/частями приложения.
    Содержит:
        - отфильтрованную доступность (AvailabilityDTO);
        - applied_criteria - это простая метка, сколько именно слотов пользователь просил проверить. Это может
          сильно пригодиться для логов и отладки в будущем (чтобы понимать, почему поиск выдал именно такой результат)
    ВАЖНО:
        - DTO НЕ содержит данных о специалисте, цене, формате, рейтинге и т.п.;
        - эти аспекты обрабатываются на уровне aggregator / UI."""

    availability: AvailabilityDTO
    applied_criteria: List[str]

    @property
    def has_match(self) -> bool:
        """has_match - это просто удобный флаг для системы (чтобы не писать везде "if result.availability.days:"),
        который показывает есть ли хотя бы один подходящий слот."""
        # any() - это встроенная функция, которая работает как "ленивый оптимист". Она идет по нашему генератору.
        # Как только она встречает хотя бы один день, где есть слоты, она тут же останавливается и возвращает: True,
        # а если она проверила все дни и везде было пусто - то вернет False.
        return any(day.slots for day in self.availability.days)

        # Простой аналогичный вариант без any:
        # for day in self.availability.days:
        #     if len(day.slots) > 0:
        #         return True
        # return False
