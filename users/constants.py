# Справочники для моделей в users/models.py
GENDER_CHOICES = [
    ("male", "мужской"),
    ("female", "женский"),
]

LANGUAGE_CHOICES = [
    ("english", "английский"),
    ("russian", "русский"),
]

THERAPY_FORMAT_CHOICES = [
    ("online", "удаленно"),
    ("offline", "встреча"),
    ("any", "любая"),
]

WORK_STATUS_CHOICES = [
    ("working", "работает"),
    ("not_working", "не работает"),
]

# Значение для валидатора по проверке максимально допустимого размера загружаемого файла в users/validators.py
# Размер = 5 мб
MAX_AVAILABLE_FILE_SIZE = 5

# Список ролей в приложении для использования в различных вью
ALLOWED_REGISTER_ROLES = ["psychologist", "client"]
