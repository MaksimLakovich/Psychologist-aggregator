from slugify import slugify


def generate_unique_slug(instance, value, slug_field="slug"):
    """Генерирует уникальный slug для определенного поля переданного экземпляра модели.
    - instance: объект модели (например, Topic или Method)
    - value: поле/строка, из которого нужно сделать slug (обычно instance.name)
    - slug_field: имя поля slug в модели (по умолчанию "slug")
    :return: Возвращает уникальный slug (строку)."""
    # ШАГ 1: преобразую исходную строку value в базовую форму slug (пример, "Панические атаки" > "panicheskie-ataki")
    base_slug = slugify(value)
    # ШАГ 2: устанавливаю текущее значение для slug в переменную slug (изначально он равен base_slug)
    slug = base_slug
    # ШАГ 3: беру класс объекта instance (например, это получится Topic) и сохраняю в переменную Model.
    # Это позволит выполнить запросы к базе через Model.objects.filter(...), не импортируя модель внутри slug.py.
    # Функция остается универсальной для любой модели - Topic, Method или Specialisation
    Model = instance.__class__
    # ШАГ 4: Запускаю цикл:
    # 1) Проверяю, есть ли в базе другой объект (не текущий instance), у которого поле slug_field = текущему slug
    # filter(**{slug_field: slug}) - ищет строки в БД, где slug_field равно slug. Например, filter(slug="trevoga").
    # .exclude(pk=instance.pk) - исключает текущий объект из поиска. Чтоб при обновлении существующего объекта
    # не считать его "конфликтом" с самим собой.
    # .exists() - возвращает True, если хотя бы одна запись найдена.
    # 2) Пока (пока существует такой другой объект), выполняется тело цикла - значит slug занят, увеличиваем
    # счетчик +1 и проверяем повторно.
    i = 1
    while Model.objects.filter(**{slug_field: slug}).exclude(pk=instance.pk).exists():
        slug = f"{base_slug}-{i}"
        i += 1
    return slug
