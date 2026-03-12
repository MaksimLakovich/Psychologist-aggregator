# Справочники для моделей в users/models.py
GENDER_CHOICES = [
    ("male", "Мужской"),
    ("female", "Женский"),
]

LANGUAGE_CHOICES = [
    ("english", "Английский"),
    ("russian", "Русский"),
]

THERAPY_FORMAT_CHOICES = [
    ("online", "Онлайн"),
    ("offline", "Личная встреча"),
    ("any", "Любая"),
]

WORK_STATUS_CHOICES = [
    ("working", "Работает"),
    ("not_working", "Не работает"),
]

AGE_BUCKET_CHOICES = [
    ("<25", "До 25 лет"),
    ("25-35", "25-35 лет"),
    ("35-45", "35-45 лет"),
    ("45-55", "45-55 лет"),
    (">55", "От 55 лет"),
]

PREFERRED_TOPIC_TYPE_CHOICES = [
    ("individual", "Индивидуальная"),
    ("couple", "Парная"),
]

CURRENCY_CHOICES = (
    ("RUB", "Российский рубль"),
    ("BYN", "Белорусский рубль"),
    ("KZT", "Казахстанский тенге"),
)

# Значение для валидатора по проверке максимально допустимого размера загружаемого файла в users/validators.py
# Размер = 5 мб
MAX_AVAILABLE_FILE_SIZE = 5

# Список ролей в приложении для использования в различных вью
ALLOWED_REGISTER_ROLES = ["psychologist", "client"]
