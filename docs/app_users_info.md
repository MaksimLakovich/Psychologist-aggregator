# 👤 Пользователи системы

В проекте используется **кастомная модель пользователя** (`AppUser(AbstractBaseUser, PermissionsMixin, TimeStampedModel)`), которая заменяет стандартного `User` в Django.

---

## <a id="title1"> 🔑 Основные особенности </a>

- Авторизация по `email`.
- Статус активности пользователя в `is_active` по умолчанию **default=False** и меняется на **True** при завершении подтверждения email/phone.
- Безопасность / Антиспам:
  - для API используется `throttle (anti-spam)` при отправке email для подтверждения регистрации / смены пароля и прочее.
  - для WEB используется `django-ratelimit` на вьюхах входа, регистрации и прочее.
- Кастомная модель пользователя (`AppUser`) расширяется дополнительными полями в зависимости от его роли в системе (*Client* / *Psychologist*):
  - модель `PsychologistProfile`.
  - модель `ClientProfile`.
- Для *Администраторов* используется только кастомная модель пользователя (`AppUser`) без какого-либо дополнительного расширения. На текущем этапе развития проекта достаточно существующих в полей в `AppUser`, где уже существует: `is_staff` и `is_superuser` + дополнительные кастомные **permissions**.
- Используется кастомный менеджер `AppUserManager(BaseUserManager)` для создания пользователей и суперпользователей.
- Возможность работы с API через JWT-токен.

---

## <a id="title2"> 🛠️ Кастомные валидаторы данных </a>

### users/validators.py:

- `validate_file_size(value)` - кастомный валидатор для проверки максимально допустимого размера загружаемого файла:
   - на данный момент установлено **5 мб**.
   - на данный момент используется для *фотографий профиля* и *сканов дипломов/сертификатов*.

---

## <a id="title3"> ⚒️ Сервисные вспомогательные функции </a>

### users/services/:

- `slug.py` / ***generate_unique_slug()*** - сервисная функция генерирует уникальный slug для переданного экземпляра модели.  
Это уникальный человекочитаемый идентификатор, который удобно использовать в URL, API и SEO вместо системного ID.


- `defaults.py` / ***default_languages()*** - сервисная функция возвращает список языков по умолчанию для модели PsychologistProfile.  
Необходима для избежания проблемы с мутабельностью данных при работе с моделями данных.


- `send_verification_email.py` / ***send_verification_email()*** - сервисная функция отправки email пользователю для подтверждения регистрации и его активации в системе. Функция поддерживает 2 сценария:
   - сценарий 1: обычное подтверждение регистрации без доп.параметров - письмо просто активирует аккаунт;
   - сценарий 2: подтверждение регистрации с resume-токеном paused-booking - после подтверждения email система не только активирует аккаунт, но и пытается завершить ранее выбранную запись к психологу.


- `throttles.py` - throttle-классы для защиты от спама:
   - защита эндпоинта регистрации и отправки письма с подтверждением email.
   - защита эндпоинта для авторизации (вход).
   - защита эндпоинта запроса повторной отправки письма с подтверждением email.
   - защита эндпоинта изменения пароля и так далее.
   - защита эндпоинта запроса на сброс пароля (ввод email).
   - защита эндпоинта подтверждения сброса пароля (подстановка нового пароля).


- `send_password_reset_email.py` / ***send_password_reset_email()*** - сервисная функция отправки пользователю письма со ссылкой для восстановления пароля.


### users/mixins/:

- `creator_mixin.py` / ***CreatorMixin()*** - миксин, который автоматически заполняет поле creator текущим пользователем при создании объекта.  
Данный миксин используется/работает только внутри сериализаторов DRF.

- `anonymous_only_mixin.py` / ***AnonymousOnlyMixin(AccessMixin)*** - миксин, который ограничивает доступ к форме/странице только для неавторизованных пользователей.   
Авторизованные пользователи не могут открыть страницу и перенаправляются на указанную в настройках.

---

## <a id="title4"> 🗃️ Статические справочники и переменные </a>

### users/constants.py:

| Название константы            | Место использования | Значение                                                                                                                                    |
|-------------------------------|--------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| `GENDER_CHOICES`              | models.py          | ("male", "мужской"), <br/> ("female", "женский"),                                                                                           |
| `LANGUAGE_CHOICES`            | models.py          | ("english", "английский"), <br/> ("russian", "русский"),                                                                                    |
| `THERAPY_FORMAT_CHOICES`      | models.py          | ("online", "удаленно"), <br/> ("offline", "встреча"), <br/> ("any", "любая"),                                                               |
| `WORK_STATUS_CHOICES`         | models.py          | ("working", "работает"), <br/> ("not_working", "не работает"),                                                                              |
| `MAX_AVAILABLE_FILE_SIZE`     | validators.py      | 5                                                                                                                                           |
| `ALLOWED_REGISTER_ROLES`      | views.py           | ["psychologist", "client"]                                                                                                                  |
| `AGE_BUCKET_CHOICES`          | models.py          | ("<25", "До 25 лет"), <br/> ("25-35", "25-35 лет"), <br/> ("35-45", "35-45 лет"), <br/> ("45-55", "45-55 лет"), <br/> (">55", "От 55 лет"), |
| `PREFERRED_TOPIC_TYPE_CHOICES` | models.py          | ("individual", "Индивидуальная"), <br/> ("couple", "Парная"),                                                                               |
| `CURRENCY_CHOICES`            | models.py          | ("RUB", "Российский рубль"), <br/> ("BYN", "Белорусский рубль"), <br/> ("KZT", "Казахстанский тенге"),                                      |

---

## <a id="title5"> 🗄️ Модели данных </a>

### users/models.py:

1. Модель `TimeStampedModel` (abstract):  
    Абстрактная модель для добавления временных меток создания и обновления.
    
    | Поле         | Тип           | Описание                                  |
    | ------------ | ------------- | ----------------------------------------- |
    | `created_at` | DateTimeField | Дата и время создания записи              |
    | `updated_at` | DateTimeField | Дата и время последнего обновления записи |

2. Модель `UserRole(TimeStampedModel)`:

    | Поле         | Тип                    | Описание                                                   |
    | ------------ | ---------------------- |------------------------------------------------------------|
    | `id`         | AutoField              | Уникальный ID роли                                         |
    | `creator`    | ForeignKey → `AppUser` | Пользователь, создавший роль (может быть `null`)           |
    | `role`       | CharField(50)          | Название роли (например: `client`, `psychologist`, `admin`) |
    | `created_at` | DateTimeField | Дата и время создания                                      |
    | `updated_at` | DateTimeField | Дата и время последнего обновления                         |

3. Модель `Topic(TimeStampedModel)`:

    | Поле         | Тип                   | Описание                                                                 |
    |--------------|-----------------------|--------------------------------------------------------------------------|
    | `id`         | AutoField             | Уникальный ID темы                                                       |
    | `creator`    | ForeignKey → `AppUser` | Пользователь, создавший тему (может быть `null`)                         |
    | `type`       | CharField(100)        | Вид запроса (например: "Индивидуальная", "Парная" и т.д.)                |
    | `group_name` | CharField(100)        | Название группы запросов (например: "Мое состояние", "Отношения" и т.д.) |
    | `name`       | CharField(255)        | Название темы (например: "Тревожность", "Выгорание" и т.п.)               |
    | `slug`       | SlugField(255)        | Уникальный slug-название темы                                            |
    | `created_at` | DateTimeField         | Дата и время создания                                                    |
    | `updated_at` | DateTimeField         | Дата и время последнего обновления                                       |

4. Модель `Specialisation(TimeStampedModel)`:

    | Поле          | Тип                    | Описание                              |
    | ------------- | ---------------------- |---------------------------------------|
    | `id`          | AutoField              | Уникальный ID специализации           |
    | `creator`     | ForeignKey → `AppUser` | Пользователь, создавший запись        |
    | `name`        | CharField(255)         | Название специализации (уникальное)   |
    | `description` | TextField              | Описание специализации                |
    | `slug`        | SlugField(255)         | Уникальный slug-название специализации |
    | `created_at`  | DateTimeField          | Дата и время создания                 |
    | `updated_at`  | DateTimeField          | Дата и время последнего обновления    |

5. Модель `Method(TimeStampedModel)`:

    | Поле          | Тип                    | Описание                           |
    | ------------- | ---------------------- |------------------------------------|
    | `id`          | AutoField              | Уникальный ID метода               |
    | `creator`     | ForeignKey → `AppUser` | Пользователь, создавший запись     |
    | `name`        | CharField(255)         | Название метода (уникальное)       |
    | `description` | TextField              | Описание метода                    |
    | `slug`        | SlugField(255)         | Уникальный slug-название метода    |
    | `created_at`  | DateTimeField          | Дата и время создания              |
    | `updated_at`  | DateTimeField          | Дата и время последнего обновления |

6. Модель `Education(TimeStampedModel)`:

    | Поле             | Тип                       | Описание                                                   |
    | ---------------- | ------------------------- |------------------------------------------------------------|
    | `id`             | AutoField                 | Уникальный ID записи об образовании                        |
    | `creator`        | ForeignKey → `AppUser`    | Пользователь, создавший запись                             |
    | `country`        | CountryField              | Страна учебного заведения                                  |
    | `institution`    | CharField(255)            | Название учебного учреждения                               |
    | `degree`         | CharField(255)            | Степень/квалификация (Бакалавр, Магистр и т.д.)            |
    | `specialisation` | CharField(255)            | Направление или программа обучения                         |
    | `year_start`     | PositiveSmallIntegerField | Год начала обучения (≥1900)                                |
    | `year_end`       | PositiveSmallIntegerField | Год окончания (может быть пустым, если обучение в процессе) |
    | `document`       | FileField                 | Скан диплома/сертификата (.pdf, .jpg, .png)                |
    | `is_verified`    | BooleanField              | Флаг модерации подлинности                                 |
    | `created_at`     | DateTimeField             | Дата и время создания                                      |
    | `updated_at`     | DateTimeField             | Дата и время последнего обновления                         |

7. Модель `AppUser(AbstractBaseUser, PermissionsMixin, TimeStampedModel)`:

    | Поле          | Тип                      | Описание                                    |
    |---------------|--------------------------|---------------------------------------------|
    | `uuid`        | UUIDField (PK)           | Уникальный идентификатор пользователя       |
    | `first_name`  | CharField(150)           | Имя                                         |
    | `last_name`   | CharField(150)           | Фамилия                                     |
    | `age`         | PositiveSmallIntegerField | Возраст пользователя (18–120 лет)           |
    | `email`       | EmailField (unique)      | Уникальный email - используется как логин   |
    | `phone_number` | PhoneNumberField         | Телефон пользователя (опционально)          |
    | `role`        | ForeignKey → `UserRole`  | Роль пользователя (клиент, психолог, админ) |
    | `timezone`    | TimeZoneField            | Часовой пояс пользователя                   |
    | `is_staff`    | BooleanField             | Признак административного доступа           |
    | `is_active`   | BooleanField             | Аккаунт активен/заблокирован                |
    | `is_superuser` | BooleanField            | Признак суперпользрвателя                   |
    | `last_login`  | DateTimeField             | Дата и время последнего входа               |
    | `created_at`  | DateTimeField            | Дата и время создания                       |
    | `updated_at`  | DateTimeField            | Дата и время последнего обновления          |

8. Модель `PsychologistProfile(TimeStampedModel)`:

    | Поле                       | Тип                          | Описание                                                        |
    |----------------------------|------------------------------|-----------------------------------------------------------------|
    | `id`                       | AutoField                    | Уникальный ID профиля психолога                                 |
    | `user`                     | OneToOneField → `AppUser`    | Связь с пользователем                                           |
    | `slug`                     | SlugField                    | Slug-полное имя                                                 |
    | `is_verified`              | BooleanField                 | Подтвержден ли профиль администратором                          |
    | `gender`                   | CharField(choices)           | Пол                                                             |
    | `specialisations`          | ManyToMany → `Specialisation` | Список специализаций (методологических школ)                    |
    | `methods`                  | ManyToMany → `Method`        | Методы или подходы, используемые психологом                     |
    | `topics`                   | ManyToMany → `Topic`         | Темы или запросы, с которыми работает психолог                  |
    | `is_all_education_verified` | BooleanField                 | Проверено ли все образование                                    |
    | `biography`                | TextField                    | Описание, биография психолога                                   |
    | `photo`                    | ImageField                   | Фотография профиля (.jpg, .jpeg, .png)                          |
    | `practice_start_year`      | PositiveSmallIntegerField    | Год начала практики для вычисления опыта работы в годах         |
    | `languages`                | ArrayField(CharField(50))    | Языки, на которых проводятся сессии (по умолчанию `["russian"]`) |
    | `therapy_format`           | CharField(choices)           | Формат работы: онлайн / офлайн / гибрид                         |
    | `price_individual`         | DecimalField(10,2)           | Стоимость индивидуальной сессии                                 |
    | `price_couples`            | DecimalField(10,2)           | Стоимость парной сессии                                         |
    | `price_currency`           | CharField(choices)           | Валюта сессии                                                   |
    | `work_status`              | CharField(choices)           | Рабочий статус (работает / не принимает / в отпуске и т.д.)     |
    | `rating`                   | DecimalField(3,1)            | Рейтинг психолога                                               |
    | `created_at`               | DateTimeField                | Дата и время создания                                           |
    | `updated_at`               | DateTimeField                | Дата и время последнего обновления                              |

9. Модель `ClientProfile(TimeStampedModel)`:

    | Поле                  | Тип                       | Описание                                               |
    |-----------------------|---------------------------|--------------------------------------------------------|
    | `id`                  | AutoField                 | Уникальный ID профиля клиента                          |
    | `user`                | OneToOneField → `AppUser` | Связь с пользователем                                  |
    | `therapy_experience`  | BooleanField              | Есть ли у клиента опыт психотерапии                    |
    | `has_preferences`     | BooleanField              | Есть ли у клиента предпочтения среди психологов        |
    | `preferred_methods`   | ManyToMany → `Method`     | Предпочтительные методы и подходы клиента              |
    | `preferred_topic_type` | CharField(choices)        | Вид консультации (индивидуальная/парная)               |
    | `requested_topics`    | ManyToMany → `Topic`      | Запросы, с которыми клиент приходит                    |
    | `preferred_ps_age`    | CharField(choices)        | Предпочитаемый возраст психолога                       |
    | `preferred_ps_gender` | CharField(choices)        | Предпочитаемый пол психолога                           |
    | `has_time_preferences` | BooleanField              | Наличие предпочтения по времени сессии                 |
    | `preferred_slots`     | ArrayField(DateTimeField) | Предпочитаемые временные слоты для сессии с учетом UTC |
    | `created_at`          | DateTimeField             | Дата и время создания                                  |
    | `updated_at`          | DateTimeField             | Дата и время последнего обновления                     |

---

## <a id="title6"> 👮🏻‍♂️ Права доступа и группы сотрудников </a>

### Права доступов

### users/permissions.py:


#### Permission-классы для DRF:

| № | Название права          | Описание                                                                                                                                                                                                     |
|---|-------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | `IsOwnerOrAdmin`        | Возвращает True, если пользователь является или "владельцем объекта" или "действующим админом". Используется для Education-эндпоинтов.                                                                       |
| 2 | `IsSelfOrAdmin`         | Возвращает True, если пользователь является или "владельцем объекта" или "действующим админом". Используется для AppUser-эндпоинтов (там нет поля Creator поэтому работаем с "obj == user")                  |
| 3 | `IsProfileOwnerOrAdmin` | Возвращает True, если пользователь является или "владельцем объекта" или "действующим админом". Используется для PsychologistProfile-эндпоинтов (там нет поля creator поэтому работаем с 'obj.user == user'). |
| 4 | `IsPsychologistOrAdmin` | Возвращает True, если пользователь является психологом ИЛИ действующим админом.                                                                                                                              |

---

## <a id="title7"> ⚙️ API-функционал </a>

### 1. СЕРИАЛИЗАТОРЫ МОДЕЛЕЙ

### users/_api/serializers.py:

Для **API-эндпоинтов** созданы следующие сериализаторы:

- Справочники приложения:
  - `TopicSerializer(CreatorMixin)`
  - `SpecialisationSerializer(CreatorMixin)`
  - `MethodSerializer(CreatorMixin)`
  - `EducationSerializer(CreatorMixin)`
  - `PublicEducationSerializer` - для вывода публичной информации в карточке психолога для любого пользователя системы (скрыты персональные данные - например скан диплома и т.д.)

  
- Аккаунт пользователя:
  - `AppUserSerializer`


- Профили пользователя:
  - `PsychologistProfileReadSerializer` - Read-сериализатор (используется для GET - создавать/редактировать вложенные объекты через него нельзя)
  - `PsychologistProfileWriteSerializer` - Write-сериализатор (используется для PATCH/PUT - разрешает модифицировать только связи через список PK)
  - `ClientProfileReadSerializer` - Read-сериализатор (используется для GET - создавать/редактировать вложенные объекты через него нельзя)
  - `ClientProfileWriteSerializer` - Write-сериализатор (используется для PATCH/PUT - разрешает модифицировать только связи через список PK)
  - `PublicPsychologistProfileSerializer` - для вывода публичной информации в карточке психолога для любого пользователя системы (скрыты персональные данные)


- Регистрация / Пароли:
  - `RegisterSerializer` - **"cериализатор-оркестр"** для регистрации пользователя с профилем (либо психолог, либо клиент). Он соединяет разные сериализаторы (AppUserSerializer + PsychologistProfileSerializer + ClientProfileSerializer), где в зависимости от выбранной роли создает связанный профиль: PsychologistProfile или ClientProfile
  - `ChangePasswordSerializer` - ***изменение пароля*** авторизованным пользователем
  - `PasswordResetSerializer` - ***сброс пароля*** неавторизованного пользователя (ввод email)
  - `PasswordResetConfirmSerializer` - ***подтверждение сброса пароля***: проверяет uid + token и меняет пароль через set_password()


- Авторизация:
  - `CustomTokenObtainPairSerializer` - ***авторизация (login)*** пользователя (получение JWT-токенов, позволяющий вход по email)
  - `LogoutSerializer` - ***выход (logout)*** пользователя (помещение токена в blacklist refresh token)


### 2. КОНТРОЛЛЕРЫ 

### users/_api/views.py:

#### 1) API 

| №  | Название контроллера                     | Тип (ViewSet / Generic)          | Описание функционала (docstring)                                                                                                                                                                                                                                             | Используемые модели                                       | Используемые сериализаторы                                               |
|----|------------------------------------------|----------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|--------------------------------------------------------------------------|
| 1  | **RegisterView**                         | `GenericAPIView`                 | Регистрация пользователя (psychologist / client). Делегирует бизнес-логику `RegisterSerializer` / сервисам. Отправка письма верификации                                                                                                                                      | `AppUser`, `PsychologistProfile`, `ClientProfile`         | `RegisterSerializer`                                                     |
| 2  | **EmailVerificationView**                | `APIView`                        | Подтверждение email после регистрации по `uid`+`token` (активация `is_active=True`)                                                                                                                                                                                          | `AppUser`                                                 | -                                                                        |
| 3  | **ResendEmailVerificationView**          | `APIView`                        | Запрос на повторное отправление email после регистрации для неактивного пользователя (если предыдущее не было использовано) (throttle: register)                                                                                                                             | `AppUser`                                                 | -                                                                        |
| 4  | **CustomTokenObtainPairView**            | `TokenObtainPairView` (SimpleJWT) | JWT-логин по email + возврат access/refresh + доп. поля (user_uuid, role) (throttle: login)                                                                                                                                                                                  | `AppUser`                                                 | `CustomTokenObtainPairSerializer`                                        |
| 5  | **LogoutAPIView**                        | `APIView`                        | Деактивация refresh-токена (blacklist)                                                                                                                                                                                                                                       | `AppUser`                                                 | `LogoutSerializer`                                                       |
| 6  | **ChangePasswordView**                   | `APIView`                        | Смена пароля аутентифицированным пользователем (валидирует old_password) (throttle: change_password)                                                                                                                                                                         | `AppUser`                                                 | `ChangePasswordSerializer`                                               |
| 7  | **PasswordResetView**                    | `APIView`                        | Forgot password - ввод email и отправка письма со ссылкой для сброса старого пароля (throttle: password_reset)                                                                                                                                                               | `AppUser`                                                 | `PasswordResetSerializer`                                                |
| 8  | **PasswordResetConfirmView**             | `APIView`                        | Подтверждения сброса пароля неавторизованного пользователя: принимает uid, token, new_password и потом set_password() (throttle: password_reset_confirm)                                                                                                                     | `AppUser`                                                 | `PasswordResetConfirmSerializer`                                         |
| 9  | **TopicListView**                        | `ListAPIView`                    | Список всех Topic (используется при выборе тем)                                                                                                                                                                                                                              | `Topic`                                                   | `TopicSerializer`                                                        |
| 10 | **TopicDetailView**                      | `RetrieveAPIView`                | Детали Topic по `slug` (вместо id)                                                                                                                                                                                                                                           | `Topic`                                                   | `TopicSerializer`                                                        |
| 11 | **SpecialisationListView**               | `ListAPIView`                    | Список Specialisation (методологическая школа)                                                                                                                                                                                                                               | `Specialisation`                                          | `SpecialisationSerializer`                                               |
| 12 | **SpecialisationDetailView**             | `RetrieveAPIView`                | Детали Specialisation по `slug` (вместо id)                                                                                                                                                                                                                                  | `Specialisation`                                          | `SpecialisationSerializer`                                               |
| 13 | **MethodListView**                       | `ListAPIView`                    | Список Method (инструмент/подход)                                                                                                                                                                                                                                            | `Method`                                                  | `MethodSerializer`                                                       |
| 14 | **MethodDetailView**                     | `RetrieveAPIView`                | Детали Method по `slug` (вместо id)                                                                                                                                                                                                                                          | `Method`                                                  | `MethodSerializer`                                                       |
| 15 | **EducationListCreateView**              | `ListCreateAPIView`              | 1) Список educations - пользователь видит только свои, админ - все. 2) Создание Education (creator ставится CreatorMixin)                                                                                                                                                    | `Education`                                               | `EducationSerializer`                                                    |
| 16 | **EducationRetrieveUpdateDestroyView**   | `RetrieveUpdateDestroyAPIView`   | CRUD для одной Education; permission - `IsOwnerOrAdmin`                                                                                                                                                                                                                      | `Education`                                               | `EducationSerializer`                                                    |
| 17 | **AppUserRetrieveUpdateView**            | `RetrieveUpdateAPIView`          | РАБОТА С АККАУНТОМ: 1) Получить / обновить данные текущего пользователя (first_name, last_name, phone, timezone и т.д.); 2) Удаление (soft - т.е. перевод в is_active=False); 3) *Пароль и технические is_staff, last_login и т.д. блокируется*                              | `AppUser`                                                 | `AppUserSerializer`                                                      |
| 18 | **PsychologistProfileRetrieveUpdateView** | `RetrieveUpdateAPIView`          | РАБОТА С ПРОФИЛЕМ (психолог): 1) Получить данные профиля психолога (read-сериализатор `PsychologistProfileReadSerializer`); 2) Обновить данные профиля психолога (write-сериализатор `PsychologistProfileWriteSerializer`); 3) Разрешать изменение many2many через списки id | `PsychologistProfile` + справочники                       | `PsychologistProfileReadSerializer`, `PsychologistProfileWriteSerializer` |
| 19 | **ClientProfileRetrieveUpdateView**      | `RetrieveUpdateAPIView`          | РАБОТА С ПРОФИЛЕМ (клиент): 1) Получить данные профиля клиента (read-сериализатор `ClientProfileReadSerializer`); 2) Обновить данные профиля психолога (write-сериализатор `ClientProfileWriteSerializer`); 3) Разрешать изменение many2many через списки id                 | `ClientProfile` + справочники                             | `ClientProfileReadSerializer`, `ClientProfileWriteSerializer`            |
| 20 | **PublicPsychologistProfileRetrieveView** | `RetrieveAPIView`                | Публичная карточка психолога (детали, без чувствительных персональных полей)                                                                                                                                                                                                 | `AppUser`, `PsychologistProfile` + справочники            | `PublicPsychologistProfileSerializer`                                    |

#### 2) AJAX-запрос (fetch) на специальный API-endpoint

| №  | Название контроллера              | Тип (ViewSet / Generic) | Описание функционала (docstring)                                                                                     | Используемые модели          |
|----|-----------------------------------|------------------------|----------------------------------------------------------------------------------------------------------------------|------------------------------|
| 1  | **SaveHasPreferencesAjaxView**    | `View`                 | Моментальное сохранение значения has_preferences выбранного клиентом в БД или гостем в session на html-странице      | `ClientProfile` + справочники |
| 2  | **SavePreferredMethodsAjaxView**  | `View`                 | Моментальное сохранение выбранных клиентом в БД или гостем в session методов в preferred_methods на html-странице    | `ClientProfile` + справочники |
| 3  | **SavePreferredTopicTypeAjaxView** | `View`                 | Моментальное сохранение значения preferred_topic_type выбранного клиентом в БД или гостем в session на html-странице | `ClientProfile` + справочники |
| 4  | **SaveRequestedTopicsAjaxView**   | `View`                 | Моментальное сохранение выбранных клиентом в БД или гостем в session тем в requested_topics на html-странице         | `ClientProfile` + справочники |
| 5  | **SavePreferredGenderAjaxView**   | `View`                 | Моментальное сохранение выбранных клиентом в БД или гостем в session значений в preferred_ps_gender на html-страницах | `ClientProfile` + справочники |
| 6  | **SavePreferredAgeAjaxView**      | `View`                 | Моментальное сохранение выбранных клиентом в БД или гостем в session значений в preferred_ps_age на html-страницах   | `ClientProfile` + справочники |
| 7  | **SaveHasTimePreferencesAjaxView** | `View`                 | Моментальное сохранение значения has_time_preferences выбранного клиентом в БД или гостем в session на html-странице | `ClientProfile` + справочники |
| 8  | **SavePreferredSlotsAjaxView**    | `View`                 | Моментальное сохранение выбранных клиентом в БД или гостем в session значений в preferred_slots на html-странице     | `ClientProfile` + справочники |


### 3. МАРШРУТЫ (РОУТЫ)

### users/_api/urls.py:

#### 1) API 

| №  | Эндпоинт                                                | HTTP-методы                    | Описание функционала                                                                                                                                                                                                                                                        |
|----|---------------------------------------------------------|--------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | `/users/api/register/psychologist/`                     | `POST`                         | Регистрация нового психолога                                                                                                                                                                                                                                                |
| 2  | `/users/api/register/client/`                           | `POST`                         | Регистрация нового клиента                                                                                                                                                                                                                                                  |
| 3  | `/users/api/verify-email/`                              | `GET`                          | Активация пользователя / Подтверждение email (uid+token) <br/> ⚠️Для проверки в Postman не нужно переходить по ссылке в полученном email, а нужно отправить запрос на данный адрес со скопированным данными из ссылки в письме: "uid": "YTU2....." и "token": "czgttd-....." |
| 4  | `/users/api/resend-verify-email/`                       | `POST`                         | Повторная отправка письма для активации (если предыдущее не было использовано)                                                                                                                                                                                              |
| 5  | `/users/api/login/`                                     | `POST`                         | JWT-аутентификация по email и паролю. Возвращает access и refresh токены                                                                                                                                                                                                    |
| 6  | `/users/api/token/refresh/`                             | `POST`                         | Обновление access-токена по refresh-токену. Стандартный эндпоинт SimpleJWT. Не требует отдельного контроллера во views.py                                                                                                                                                   |
| 7  | `/users/api/logout/`                                    | `POST`                         | Blacklist refresh (logout)                                                                                                                                                                                                                                                  |
| 8  | `/users/api/change-password/`                           | `POST`                         | Смена пароля с валидацией старого (auth required)                                                                                                                                                                                                                           |
| 9  | `/users/api/password-reset/`                            | `POST`                         | Forgot password - сброс пароля неавторизованного пользователя (забыл пароль)                                                                                                                                                                                                |
| 10 | `/users/api/password-reset-confirm/`                    | `POST`                         | Подтверждение сброса пароля (uid+token + new_password). <br/> ⚠️Для проверки в Postman не нужно переходить по ссылке в полученном email, а нужно отправить запрос на данный адрес со скопированным данными из ссылки в письме: "uid": "YTU2....." и "token": "czgttd-....." |
| 11 | `/users/api/topics/`                                    | `GET`                          | Список всех Topics                                                                                                                                                                                                                                                          |
| 12 | `/users/api/topics/<slug:slug>/`                        | `GET`                          | Детали Topic по slug (вместо id)                                                                                                                                                                                                                                            |
| 13 | `/users/api/specialisations/`                           | `GET`                          | Список всех Specialisations                                                                                                                                                                                                                                                 |
| 14 | `/users/api/specialisations/<slug:slug>/`               | `GET`                          | Детали Specialisations по slug (вместо id)                                                                                                                                                                                                                                  |
| 15 | `/users/api/methods/`                                   | `GET`                          | Список всех Methods                                                                                                                                                                                                                                                         |
| 16 | `/users/api/methods/<slug:slug>/`                       | `GET`                          | Детали Method по slug (вместо id)                                                                                                                                                                                                                                           |
| 17 | `/users/api/educations/`                                | `GET`, `POST`                  | Список Education / создание Education (пользователь видит только свои)                                                                                                                                                                                                      |
| 18 | `/users/api/educations/<int:pk>/`                       | `GET`, `PUT`, `PATCH`, `DELETE` | Полный CRUD для Education (владельцу и админу)                                                                                                                                                                                                                              |
| 19 | `/users/api/my-account/`                                | `GET`, `PUT`, `PATCH`, `DELETE` | Получить / обновить / soft-удалить текущего пользователя (`AppUser`) (auth required)                                                                                                                                                                                        |
| 20 | `/users/api/my-psychologist-profile/`                   | `GET`, `PUT`, `PATCH`          | Получить / обновить своего `PsychologistProfile` (auth required, role=psychologist)                                                                                                                                                                                         |
| 21 | `/users/api/my-client-profile/`                         | `GET`, `PUT`, `PATCH`          | Получить / обновить своего `ClientProfile` (auth required, role=client)                                                                                                                                                                                                     |
| 22 | `/users/api/psychologists/<uuid:uuid>/`                 | `GET`                          | Получить публичную карточку психолога (без чувствительных персональных данных)                                                                                                                                                                                              |

#### 2) AJAX-запросы (fetch) на моментальное сохранение указанных клиентом на html-страницах данных в БД

| №  | Эндпоинт                                              | HTTP-методы | Описание функционала                                                                       |
|----|-------------------------------------------------------|------------|--------------------------------------------------------------------------------------------|
| 1  | `/users/api/save-has-preferences/`                    | `POST`     | Моментальное сохранение значения has_preferences выбранного клиентом на html-страницах     |
| 2  | `/users/api/save-preferred-methods/`                  | `POST`     | Моментальное сохранение выбранных клиентом методов в preferred_methods на html-страницах   |
| 3  | `/users/api/save-preferred-topic-type/`               | `POST`     | Моментальное сохранение значения preferred_topic_type выбранного клиентом на html-страницах |
| 4  | `/users/api/save-requested-topics/`                   | `POST`     | Моментальное сохранение выбранных клиентом тем в requested_topics на html-страницах        |
| 5  | `/users/api/save-preferred-gender/`                   | `POST`     | Моментальное сохранение выбранных клиентом значений в preferred_ps_gender на html-страницах |
| 6  | `/users/api/save-preferred-age/`                      | `POST`     | Моментальное сохранение выбранных клиентом значений в preferred_ps_age на html-страницах   |
| 7  | `/users/api/save-has-time-preferences/`               | `POST`     | Моментальное сохранение значения has_time_preferences выбранного клиентом на html-страницах |
| 8  | `/users/api/save-preferred-slots/`                    | `POST`     | Моментальное сохранение выбранных клиентом значений в preferred_slots на html-страницах    |

---

## <a id="title8"> 🖥️ WEB-функционал </a>

### 1. ФОРМЫ

### users/_web/forms/:

Для **WEB-эндпоинтов** созданы следующие формы:

#### auth_form.py:
- Авторизация / Регистрация:
  - `AppUserRegistrationForm(forms.ModelForm)` - форма для ***регистрации (registration)*** нового пользователя.
  - `AppUserLoginForm(AuthenticationForm)` - форма для ***авторизации (login)*** ранее зарегистрированного пользователя.

#### reset_password_form.py:
- Восстановление пароля (неавторизованный пользователь):
  - `PasswordResetRequestForm(forms.Form)` - форма для запроса ***восстановления пароля (reset)*** неавторизованным пользователем.
  - `PasswordResetConfirmForm(forms.Form)` - форма для ***подтверждения сброса пароля (confirm)*** через uid/token и установку нового пароля.

#### change_password_form.py:
- Изменение пароля (авторизованный пользователь):
  - `ChangePasswordForm(forms.Form)` - форма для ***смены пароля (change)*** авторизованного пользователя.

#### edit_client_form.py:
- Редактирование данных пользователя:
  - `EditClientProfileForm(forms.ModelForm)` - форма для ***редактирования данных*** профиля клиента.


### 2. КОНТРОЛЛЕРЫ 

### users/_web/views/:

#### auth_view.py:

| № | Название контроллера            | Тип (ViewSet / Generic)            | Описание функционала (docstring)                                                                                                                                                                                                                                                                                                                                                                  | Используемые модели       | Используемые формы        |
|---|---------------------------------|------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|---------------------------|
| 1 | **CompleteBookingAuthPageView** | `AnonymousOnlyMixin, TemplateView` | 1) Отдельный экран выбора следующего шага для гостя с paused-booking. Экран появляется только после того, как гость уже выбрал специалиста и слот, а система поставила запись на паузу до аутентификации <br/> 2) Работает с двумя сценариями: - сценарий 1: гость уже есть в БД (то есть ранее регистрировался); - сценарий 2: гость новый пользователь и его нет в БД                           | `AppUser`, `ClientProfile` | -                         |
| 2 | **RegisterPageView**            | `AnonymousOnlyMixin, FormView`     | 1) Регистрации нового пользователя в системе (всегда первоначально регистрируется с профилем "Клиент"); <br/> 2) Отправка письма верификации; <br/> 3) Работает с двумя сценариями: - сценарий 1: обычная регистрация без paused-booking; - сценарий 2: регистрация после выбора психолога и слота, где после подтверждения email система должна попытаться завершить paused-booking автоматически | `AppUser`, `ClientProfile` | `AppUserRegistrationForm` |
| 3 | **VerifyEmailView**             | `AnonymousOnlyMixin, View`         | 1) Верификация email после регистрации по `uid`+`token` (активация `is_active=True`); <br/> 2) Работает с двумя сценариями: - сценарий 1: обычное подтверждение email без resume-booking; - сценарий 2: подтверждение email с resume-booking, где после активации система пытается автоматически завершить ранее выбранную запись                                                                 | `AppUser`                 | -                         |
| 4 | **LoginPageView**               | `AnonymousOnlyMixin, LoginView`    | 1) Вход ранее зарегистрированного пользователя в систему; <br/> 2) Работает с двумя сценариями: - сценарий 1: обычный вход без paused-booking; - сценарий 2: вход "гостя" после выбора психолога и слота, где после подтверждения email система должна попытаться завершить paused-booking автоматически                                                                                          | `AppUser`                 | `AppUserLoginForm`        |

#### reset_password_view.py:

| № | Название контроллера             | Тип (ViewSet / Generic)        | Описание функционала (docstring)                                                                                                             | Используемые модели       | Используемые формы         |
|---|----------------------------------|--------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|----------------------------|
| 1 | **PasswordResetRequestPageView** | `AnonymousOnlyMixin, FormView` | Web-контроллер для запроса восстановления пароля по email (неавторизованный пользователь)                                                    | `AppUser`                 | `PasswordResetRequestForm` |
| 2 | **PasswordResetConfirmPageView** | `AnonymousOnlyMixin, FormView` | Web-контроллер для подтверждения сброса пароля по uid/token и установке нового пароля                                                       | `AppUser`                 | `PasswordResetConfirmForm` |

#### ratelimit_view.py

| № | Название контроллера       | Описание функционала (docstring)                                                                                             |
|---|----------------------------|------------------------------------------------------------------------------------------------------------------------------|
| 1 | **def ratelimited_view()** | Отображает понятную страницу для случаев превышения лимитов запросов (django-ratelimit). Красивая обработка ошибок 403 и 429 |

#### change_password_view.py

| № | Название контроллера       | Тип (ViewSet / Generic)        | Описание функционала (docstring)                             |
|---|----------------------------|--------------------------------|--------------------------------------------------------------|
| 1 | **ChangePasswordPageView** | `LoginRequiredMixin, FormView` | Web-контроллер для смены пароля авторизованного пользователя |

#### edit_client_view.py

| № | Название контроллера          | Тип (ViewSet / Generic)        | Описание функционала (docstring)                  |
|---|-------------------------------|--------------------------------|---------------------------------------------------|
| 1 | **EditClientProfilePageView** | `LoginRequiredMixin, FormView` | Web-контроллер для редактирования профиля клиента |


### 3. HTML-ШАБЛОНЫ

### users/templates/users/:

| № | html-страница                     | Описание                                                                                                                                                                                       |
|---|-----------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | `register_page.html`              | Страница для регистрации нового пользователя в приложении (всегда первоначально регистрируется новый пользователь как КЛИЕНТ, а не специалист)                                                 |
| 2 | `complete_booking_auth_page.html` | Страница выбора следующего шага для гостя с paused-booking. Экран появляется только после того, как гость уже выбрал специалиста и слот, а система поставила запись на паузу до аутентификации |
| 3 | `login_page.html`                 | Страница для авторизации пользователя в приложении                                                                                                                                             |
| 4 | `ratelimited.html`                | Страница для отображения понятной страницы для случаев превышения лимитов запросов (django-ratelimit). Красивое информирование о блокировке при борьбе с анти-спамом (ошибки 403/429)          |
| 5 | `password_reset_request_page.html` | Страница для запроса восстановления пароля по email (неавторизованный пользователь)                                                                                                            |
| 6 | `password_reset_confirm_page.html` | Страница для подтверждения сброса пароля по uid/token и установке нового пароля                                                                                                                |
| 7 | `change_password.html`            | Страница для изменения пароля                                                                                                                                                                  |
| 8 | `edit_client.html`                | Страница для редактирвоания данных пользователя                                                                                                                                                |

### 4. МАРШРУТЫ (РОУТЫ)

### users/_web/urls.py:

| № | Эндпоинт                 | HTTP-методы  | Описание функционала                                                                                                                                                                                  |
|---|--------------------------|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | `register/`              | `POST`       | Регистрация нового пользователя в системе (всегда первоначально регистрируется новый пользователь как КЛИЕНТ, а не специалист)                                                                        |
| 2 | `complete-booking-auth/` | `GET`        | Отдельный экран выбора следующего шага для гостя с paused-booking. Экран появляется только после того, как гость уже выбрал специалиста и слот, а система поставила запись на паузу до аутентификации |
| 3 | `verify-email/`          | `GET`        | Активация пользователя / Подтверждение email (uid+token)                                                                                                                                              |
| 4 | `login/`                 | `POST`       | Авторизация (Login) ранее зарегистрированного пользователя в системе                                                                                                                                  |
| 5 | `logout/`                | `POST`       | Выход (Logout)                                                                                                                                                                                        |
| 6 | `password-reset/`        | `POST`       | Восстановление пароля по email (неавторизованный пользователь)                                                                                                                                        |
| 7 | `password-reset-confirm/` | `GET`, `POST` | Подтверждение сброса пароля по uid/token и установке нового пароля                                                                                                                                    |
| 8 | `password-change/`       | `POST`       | Изменение пароля (авторизованный пользователь)                                                                                                                                                        |
| 9 | `profile-edit/`          | `GET`, `POST` | Редактирования пользовательских данных                                                                                                                                                                |

---

## <a id="title9"> 👩‍💻 Админки </a>

### users/admins.py:

1. Авторизация в админке (http://base_url/admin/) через встроенные механизмы Django.

2. Список админок:
   - ☆ `UserRoleAdmin`
   - ☆ `TopicAdmin`
   - ☆ `SpecialisationAdmin`
   - ☆ `MethodAdmin`
   - ☆ `EducationAdmin`
   - ★ `AppUserAdmin`
   - ⭐️`PsychologistProfileAdmin`
   - ⭐️`ClientProfileAdmin`

---

## <a id="title10"> ℹ️ Менеджер пользователей </a>

### users/managers.py:

`AppUserManager(BaseUserManager)` - кастомный менеджер для работы с пользователями.

#### Методы менеджера:
- `create_user(email, password, **extra_fields)` - создает и возвращает обычного пользователя с указанным email и password.
- `create_superuser(email, password, **extra_fields)` - создает и возвращает суперпользователя с расширенными правами доступа.

> ⚠️ Валидация: Email и пароль обязательны.

---

## <a id="title11"> 📌 Создание суперпользователя </a>

1. Создание суперпользователя **локально** для теста:
```commandline
python manage.py createsuperuser
```

2. Создание суперпользователя на **сервере** в проме:
```commandline
docker exec -it <container_name_web> python manage.py createsuperuser
```

---

## <a id="title12"> 👥 Создание тестовых психологов в БД </a>

**Описание файла с тестовыми психологами для проверки работы агрегатора/публичного каталога/фильтрации: [fixture_users_psychologists_info.md](fixture_users_psychologists_info.md)**
