from dataclasses import dataclass
from datetime import date, time
from typing import List


@dataclass(frozen=True)
class SlotDTO:
    """DTO-объект с нарезанными доменными слотами рабочего окна по правилам домена.
        - frozen=True делает объект "замороженным/неизменяемым" - после создания нельзя поменять start/duration.
        - Цель: DTO-объект, предназначен только для транспортировки данных между слоями/частями приложения.
    Слот не привязан ни к пользователю, ни к психологу - это позволит:
        - использовать его в агрегированном matching;
        - кешировать;
        - сравнивать."""

    day: date
    start: time
    end: time


@dataclass(frozen=True)
class AvailabilityDayDTO:
    """DTO-объект с доступными слотами специалиста для одного рабочего дня по его персональным правилам.
        - frozen=True делает объект "замороженным/неизменяемым" - после создания нельзя поменять start/duration.
        - Цель: DTO-объект, предназначен только для транспортировки данных между слоями/частями приложения."""

    day: date
    slots: List[SlotDTO]


@dataclass(frozen=True)
class AvailabilityDTO:
    """DTO-объект с доступными слотами в диапазоне дат [date_from, date_to] включительно.
        - frozen=True делает объект "замороженным/неизменяемым" - после создания нельзя поменять start/duration.
        - Цель: DTO-объект, предназначен только для транспортировки данных между слоями/частями приложения."""

    days: List[AvailabilityDayDTO]
