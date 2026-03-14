from django.utils import timezone


def build_calendar_slot_time_display(*, slot, client_timezone) -> dict:
    """Готовит итоговые display-данные слота (время начала и окончания) в текущем timezone клиента.

    Бизнес-смысл:
        - сама встреча хранится в БД в timezone-aware datetime;
        - но личный кабинет клиента должен всегда показывать время с адаптацией под его текущем timezone;
        - это правило используется на разных страницах отображения событий (например, "Запланированные" или
          на других календарных страницах клиента "Архив" или detail-экран сессии).

    Возвращает только финальные display-поля:
        - display_date: дата встречи в формате для UI;
        - display_day_key: ключ дня для month-widget календаря;
        - display_time_range: строка времени начала и конца встречи;
        - display_client_timezone: timezone клиента для подписи в интерфейсе;
        - display_start_iso / display_end_iso: ISO-значения для JS-календаря и других frontend-виджетов.
    """
    start_client_tz = timezone.localtime(slot.start_datetime, client_timezone)
    end_client_tz = timezone.localtime(slot.end_datetime, client_timezone)

    return {
        "display_date": start_client_tz.strftime("%d.%m.%Y"),
        "display_day_key": start_client_tz.strftime("%Y-%m-%d"),
        "display_time_range": f"{start_client_tz.strftime('%H:%M')} - {end_client_tz.strftime('%H:%M')}",
        "display_client_timezone": str(client_timezone),
        "display_start_iso": start_client_tz.isoformat(),
        "display_end_iso": end_client_tz.isoformat(),
    }
