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
        - список примененных доменных критериев (для отладки / аудита).
    ВАЖНО:
        - DTO НЕ содержит данных о специалисте, цене, формате, рейтинге и т.п.;
        - эти аспекты обрабатываются на уровне aggregator / UI."""

    availability: AvailabilityDTO
    applied_criteria: List[str]
