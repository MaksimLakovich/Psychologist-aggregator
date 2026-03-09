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

## <a> ШАГ 1: Команда для запуска загрузки данных </a>

Загрузка **локально** для теста:
```bash
python manage.py loaddata fixtures/users_psychologists.json
```

### Пример записи `AppUser + PsychologistProfile`
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
      "password": "pbkdf2_sha256$1000000$3P22RzgDOnRY2MTm5HWrE2$VhaGsqiUVK+ijrya/tG3ouLDR8tARYvTPCkRpfizGII=",
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
      "topics": [1, 3, 5, 6, 12, 22],
      "biography": "Работаю с тревожностью и самооценкой, использую КПТ и психодраму. Веду терапию для людей, уставших от постоянного стресса и эмоционального напряжения. В работе делаю упор на практические техники, осознанность и безопасное исследование внутренних сценариев. Помогаю клиентам научиться выстраивать личные границы, управлять эмоциями и постепенно возвращать чувство контроля над своей жизнью.",
      "photo": "fake_avatars/f-1.jpeg",
      "practice_start_year": 2018,
      "languages": ["russian"],
      "therapy_format": "online",
      "price_individual": "3500",
      "price_couples": "5500",
      "price_currency": "RUB",
      "work_status": "working",
      "rating": "0.0",
      "is_all_education_verified": true,
      "created_at": "2025-11-25T16:55:32.525181+03:00",
      "updated_at": "2025-11-25T16:55:32.525181+03:00",
      "slug": "irina-ivanova"
    }
  }
]
```

---

## <a> ШАГ 2: Команда для запуска загрузки данных об образовании психологов</a>

Загрузка **локально** для теста:
```bash
python manage.py loaddata fixtures/users_ps_education.json
```

### Пример записи `Education`
```json
[
  {
    "model": "users.education",
    "pk": 4,
    "fields": {
      "creator": "11111111-1111-4111-8111-111111111111",
      "country": "RU",
      "institution": "Московский государственный университет имени М. В. Ломоносова (МГУ)",
      "degree": "Магистр",
      "specialisation": "Клиническая психология",
      "year_start": 2010,
      "year_end": 2015,
      "document": "education_docs/2025/11/04/Снимок_экрана_2025-11-04_в_20.42.53.png",
      "is_verified": true,
      "created_at": "2025-11-25T16:55:32.525181+03:00",
      "updated_at": "2025-11-25T16:55:32.525181+03:00"
    }
  }
]
```

---

## <a> ШАГ 3: Команда для запуска загрузки данных об персональном рабочем расписании психологов</a>

Загрузка **локально** для теста:
```bash
python manage.py loaddata fixtures/users_ps_availability_rule.json
```

### Пример записи `AvailabilityRule + AvailabilityRuleTimeWindow`
```json
[
  {
    "model": "calendar_engine.availabilityrule",
    "pk": 1,
    "fields": {
      "creator": "11111111-1111-4111-8111-111111111111",
      "timezone": "Europe/Minsk",
      "rule_start": "2024-01-01",
      "rule_end": null,
      "weekdays": [0,1,2,3,4,5,6],
      "session_duration_individual": 50,
      "session_duration_couple": 90,
      "break_between_sessions": 10,
      "is_active": true,
      "created_at": "2026-01-20T12:00:00.000Z",
      "updated_at": "2026-01-20T12:00:00.000Z",
      "minimum_booking_notice_hours": 1
    }
  },
  {
    "model": "calendar_engine.availabilityruletimewindow",
    "pk": 1,
    "fields": {
      "rule": 1,
      "start_time": "00:00:00",
      "end_time": "00:00:00",
      "created_at": "2026-01-20T12:00:00.000Z",
      "updated_at": "2026-01-20T12:00:00.000Z"
    }
  }
]
```

---

## <a> JSON-файлы </a>

Расположение JSON-файла в структуре проекта: 
- [fixtures/users_psychologists.json](/Users/maksym/PycharmProjects/Psychologist-aggregator/fixtures/users_psychologists.json)
- [fixtures/users_ps_education.json](/Users/maksym/PycharmProjects/Psychologist-aggregator/fixtures/users_ps_education.json)
- [fixtures/users_ps_availability_rule.json](/Users/maksym/PycharmProjects/Psychologist-aggregator/fixtures/users_ps_availability_rule.json)
