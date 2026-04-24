from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone as django_timezone


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


def get_local_date_for_user(user=None) -> date:
    """Возвращает текущую дату в часовом поясе пользователя.

        Это нужно для правил расписания: дата "сегодня" должна считаться не по серверу,
        а по часовому поясу специалиста, который настраивает свое рабочее время в своем TZ.

    :param user: Функция принимает объект пользователя. "user=None" значит, что если мы никого не передадим,
    то код не "сломается", а просто сработает по стандартному сценарию.
    """
    timezone_value = getattr(user, "timezone", None)

    # Защита: если мы не знаем, где живет пользователь, мы возвращаем "сегодняшнюю дату" по проекту (settings.py)
    if timezone_value is None:
        return django_timezone.localdate()

    # Проверка на готовый объект (Умный часовой пояс).
    # Иногда в поле timezone лежит не просто текст, а уже готовый объект (например, из библиотеки pytz).
    # Метод utcoffset - это верный признак того, что объект "умный" и уже знает свой сдвиг относительно Гринвича.
    # В этом случае мы просто просим Django посчитать дату, используя этот объект.
    if hasattr(timezone_value, "utcoffset"):
        return django_timezone.localdate(timezone=timezone_value)

    # Если в timezone_value лежит просто строка (например, "Asia/Almaty"), Django не поймет ее напрямую.
    # str(timezone_value) - приводим к строке на всякий случай;
    # ZoneInfo(...) - магия Python, которая находит город в базе часовых поясов и понимает, сколько там сейчас времени;
    # django_timezone.localdate(...) - выдает итоговую дату (год, месяц, число)
    return django_timezone.localdate(timezone=ZoneInfo(str(timezone_value)))


def _time_to_minutes(value: time) -> int:
    """Переводит время в минуты от начала суток для простого сравнения нескольких временных окон."""
    return value.hour * 60 + value.minute


def time_windows_have_overlap(windows, *, start_key: str, end_key: str) -> bool:
    """Проверяет, пересекаются ли временные окна внутри одного набора.

        Важно для бизнеса:
            - 00:00-00:00 означает круглосуточно и не может сочетаться с другими окнами;
            - 09:00-00:00 означает работу до конца текущих суток;
            - 22:00-02:00 здесь не поддерживаем, такое расписание нужно оформить двумя окнами;
            - окна не должны занимать одно и то же время или пересекаться между собой.
    """
    ranges = []

    for window in windows:  # ???
        start = window.get(start_key)  # ???
        end = window.get(end_key)  # ???

        if start is None or end is None:
            continue

        start_minutes = _time_to_minutes(start)
        end_minutes = _time_to_minutes(end)

        # 00:00 как конец окна в бизнес-логике означает "до конца текущих суток", поэтому тут нам нужно отдельно
        # перевести "00:00" в 24*60=1440, иначе _time_to_minutes(00:00) вернет 0 и сработает выход ниже
        # на проверке "start_minutes > end_minutes", а конкретно для 00:00 этого не должно произойти
        if end == time(0, 0):
            end_minutes = 24 * 60

        # Некорректные окна проверяются в формах/сериализаторах/моделях.
        # Здесь просто не смешиваем проверку пересечений с проверкой валидности одного окна, просто проверяем, что
        # окончание больше начала и не позволяем создать окно например "с 14-00 до 09-00"
        if start_minutes > end_minutes:
            continue

        ranges.append((start_minutes, end_minutes))

    ranges.sort(key=lambda item: item[0])  # ???

    for index in range(1, len(ranges)):  # ???
        previous_start, previous_end = ranges[index - 1]  # ???
        current_start, current_end = ranges[index]  # ???

        if current_start < previous_end:
            return True

    return False
