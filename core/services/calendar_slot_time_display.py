from django.utils import timezone
from django.utils.formats import date_format


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
        - display_month_short / display_day_number / display_weekday: части даты для карточек и badge-блоков;
        - display_client_timezone: timezone клиента для подписи в интерфейсе;
        - display_start_iso / display_end_iso: ISO-значения для JS-календаря и других frontend-виджетов.
    """
    # Доп защита: У нас в системе TZ обязательное поле при регистрации и его невозможно очистить при редактирвоании
    # профиля, но если у клиента timezone по каким-то причинам не пришел из профиля, то все равно показываем время
    # в одном и том же предсказуемом часовом поясе приложения, а не строку "None" в интерфейсе
    effective_timezone = client_timezone or timezone.get_default_timezone()

    start_client_tz = timezone.localtime(slot.start_datetime, effective_timezone)
    end_client_tz = timezone.localtime(slot.end_datetime, effective_timezone)
    now_client_tz = timezone.localtime(timezone.now(), effective_timezone)

    return {
        "display_date": start_client_tz.strftime("%d.%m.%Y"),
        "display_day_key": start_client_tz.strftime("%Y-%m-%d"),
        "display_time_range": f"{start_client_tz.strftime('%H:%M')} - {end_client_tz.strftime('%H:%M')}",
        "display_month_short": date_format(start_client_tz, "E"),
        "display_day_number": date_format(start_client_tz, "d"),
        "display_weekday": date_format(start_client_tz, "l"),
        "display_client_timezone": str(effective_timezone),
        "display_start_iso": start_client_tz.isoformat(),
        "display_end_iso": end_client_tz.isoformat(),
        "is_today": start_client_tz.date() == now_client_tz.date(),
    }
