from datetime import date, datetime, time, timedelta


def normalize_range(day: date, start: time, end: time) -> tuple[datetime, datetime]:
    """Нужно сравнивать datetime, а не time, чтобы корректно учитывать интервалы, пересекающие границу суток.

        - Исключает ситуации, когда "end < start" и интервал фактически "ломается".
          Это проблема для слотов с "end = 00:00" и "start = 23:00", где получалось что end больше start
          и это приводило к багу;
        - Для этого выполняем нормализацию диапазонов в datetime и если "end <= start", то тогда считается,
          что диапазон пересекает полночь и автоматически добавляем +1 календарный день.
    """
    start_dt = datetime.combine(day, start)
    end_dt = datetime.combine(day, end)

    if end <= start:
        end_dt += timedelta(days=1)

    return start_dt, end_dt
