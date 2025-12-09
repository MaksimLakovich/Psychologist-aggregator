# 🗂️ Создание тестовых психологов в БД

- Описана фикстура для создания в БД 40 тестовых психологов в формате json
- Указана команда запуска загрузки данных
- ⚠️ После загрузки фикстуры в БД необходимо установить захешированный пароль для всех тестовых психологов.  
Так как пароль должен быть захеширован, то меняем его с помощью `shell`:
  - Шаг 1 - запуск shell:
    ```bash
    python manage.py shell
    ```
  
  - Шаг 2 - выполняем скрипт в shell:
    ```shell
    from users.models import AppUser
    from django.contrib.auth.hashers import make_password
    
    new_pass = make_password("123456qwe")
    
    for user in AppUser.objects.filter(role=1):
        user.password = new_pass
        user.save()
    ```

---

## <a> 1. Команда для запуска загрузки данных </a>

Загрузка **локально** для теста:
```bash
python manage.py loaddata fixtures/users_psychologists.json
```

---

## <a> 2. Пример записи</a>
```json
[
  {
    "model": "users.appuser",
    "pk": "11111111-1111-4111-8111-111111111111",
    "fields": {
      "first_name": "Ирина",
      "last_name": "Иванова",
      "age": 31,
      "email": "ps_test_1@example.com",
      "phone_number": "+375291234567",
      "role": 1,
      "timezone": "Europe/Minsk",
      "is_staff": false,
      "is_active": true,
      "is_superuser": false,
      "password": "123456qwe",
      "created_at": "2025-11-25T16:55:32.525181+03:00",
      "updated_at": "2025-11-25T16:55:32.525181+03:00"
    }
  },
  {
    "model": "users.psychologistprofile",
    "pk": 1,
    "fields": {
      "user": "11111111-1111-4111-8111-111111111111",
      "is_verified": true,
      "gender": "female",
      "specialisations": [2],
      "methods": [13, 3],
      "topics": [1, 3, 6],
      "biography": "Работаю с тревожностью и самооценкой, использую КПТ и психодраму. Веду терапию для тех, кто устал от постоянного стресса и хочет вернуть контроль над эмоциями. Практический подход + проработка сценариев в безопасном пространстве. Помогаю наладить границы и ресурсы.",
      "photo": "/fake_avatars/f-1.jpeg",
      "work_experience": 7,
      "languages": ["russian"],
      "therapy_format": "online",
      "price_individual": "3500.00",
      "price_couples": "3500.00",
      "work_status": "working",
      "rating": "0.0",
      "is_all_education_verified": true,
      "created_at": "2025-11-25T16:55:32.525181+03:00",
      "updated_at": "2025-11-25T16:55:32.525181+03:00"
    }
  }
]
```

---

## <a> 3. JSON-файл </a>

Расположение JSON-файла в структуре проекта: [fixtures/users_psychologists.json](/Users/maksym/PycharmProjects/Psychologist-aggregator/fixtures/users_psychologists.json)
