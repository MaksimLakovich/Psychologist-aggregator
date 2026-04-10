/**
 * Скрипт управляет режимами просмотра/редактирования формы профиля клиента.
 * Логика простая:
 * 1) При загрузке страницы ставим поля в "режим просмотра" (readonly/disabled).
 * 2) При нажатии "Редактировать" включаем редактирование и показываем кнопки "Сохранить/Отмена".
 * 3) При нажатии "Отмена" возвращаем исходные значения формы и снова блокируем поля.
 */

document.addEventListener("DOMContentLoaded", function () {
  // Одноразовый флаг: отключаем вступительные анимации на следующую загрузку страницы.
  // Нужен для UX после действий пользователя (submit/cancel), чтобы блоки формы не "прыгали" повторно.
  const SKIP_INTRO_ANIMATIONS_ONCE_KEY = "profileEditSkipIntroAnimationsOnce";

  const form = document.getElementById("profile-edit-form");
  if (!form) return;

  const toggleBtn = document.getElementById("profile-edit-toggle");
  const cancelBtn = document.getElementById("profile-edit-cancel");
  const editActions = document.getElementById("profile-edit-actions");
  const displayActions = document.getElementById("display-actions");
  const hasErrors = form.dataset.hasErrors === "1";

  /**
   * Если ранее был установлен флаг пропуска анимаций,
   * снимаем анимационные классы и делаем элементы сразу видимыми.
   */
  function applySkipIntroAnimationsIfNeeded() {
    const shouldSkip = sessionStorage.getItem(SKIP_INTRO_ANIMATIONS_ONCE_KEY) === "1";
    if (!shouldSkip) return;

    const animatedBlocks = document.querySelectorAll(".animate-fade-in-up, .animate-fade-in-left");
    animatedBlocks.forEach((el) => {
      el.classList.remove("animate-fade-in-up", "animate-fade-in-left");
      el.style.opacity = "1";
      el.style.animation = "none";
    });

    // Флаг одноразовый: применили и сразу очищаем.
    sessionStorage.removeItem(SKIP_INTRO_ANIMATIONS_ONCE_KEY);
  }

  /**
   * Помечаем, что при следующей загрузке страницы нужно пропустить вступительные анимации.
   */
  function markSkipIntroAnimationsOnce() {
    sessionStorage.setItem(SKIP_INTRO_ANIMATIONS_ONCE_KEY, "1");
  }

  // Все поля, которые можно редактировать (email исключаем)
  const inputs = form.querySelectorAll('input:not([name="email"]), select');
  const initialValues = {
    firstName: document.getElementById("initial-first-name")?.value ?? "",
    lastName: document.getElementById("initial-last-name")?.value ?? "",
    age: document.getElementById("initial-age")?.value ?? "",
    email: document.getElementById("initial-email")?.value ?? "",
    phone: document.getElementById("initial-phone")?.value ?? "",
    timezone: document.getElementById("initial-timezone")?.value ?? "",
  };

  /**
   * Переключает форму между режимом просмотра и редактирования.
   * @param {boolean} isEditing - true, если включаем редактирование.
   */
  function setEditMode(isEditing) {
    // Служебный флаг на форме: используется CSS-правилом для focus-стилей только в режиме редактирования.
    form.dataset.editMode = isEditing ? "1" : "0";

    inputs.forEach((input) => {
      const viewClasses = input.dataset.viewClass || input.className;
      const editClasses = input.dataset.editClass || input.className;
      if (isEditing) {
        input.removeAttribute("readonly");
        input.disabled = false;
        input.className = editClasses;
      } else {
        if (input.tagName !== "SELECT") {
          input.setAttribute("readonly", "readonly");
        }
        if (input.tagName === "SELECT") {
          input.disabled = true;
        }
        input.className = viewClasses;
      }
    });

    if (isEditing) {
      editActions.classList.remove("hidden");
      displayActions.classList.add("hidden");
    } else {
      editActions.classList.add("hidden");
      displayActions.classList.remove("hidden");
    }
  }

  // Инициализация: показываем режим просмотра
  applySkipIntroAnimationsIfNeeded();
  setEditMode(hasErrors);

  // Если пользователь нажал "Сохранить изменения" и страница перерендерилась (ошибка/успех),
  // при следующей загрузке анимации не запускаем повторно.
  form.addEventListener("submit", function () {
    markSkipIntroAnimationsOnce();
  });

  // Кнопка "Редактировать"
  toggleBtn.addEventListener("click", function () {
    setEditMode(true);
  });

  // Кнопка "Отмена"
  cancelBtn.addEventListener("click", function () {
    // На случай, если после отмены будет любой сценарий перезагрузки/перехода,
    // вступительные анимации на следующем открытии этой страницы не повторяем.
    markSkipIntroAnimationsOnce();

    // Если форма сейчас находится в состоянии серверной ошибки (POST с невалидными данными),
    // то обычный локальный reset недостаточен:
    // 1) серверные тексты ошибок останутся на экране;
    // 2) браузер будет считать текущую страницу результатом POST и при refresh покажет prompt.
    //
    // Решение: уходим на тот же URL через GET c replace(), чтобы:
    // - полностью очистить ошибки;
    // - заменить текущую POST-страницу в истории;
    // - убрать предупреждение о повторной отправке формы при обновлении.
    if (hasErrors) {
      const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      window.location.replace(currentUrl);
      return;
    }

    const firstNameField = form.querySelector('input[name="first_name"]');
    const lastNameField = form.querySelector('input[name="last_name"]');
    const ageField = form.querySelector('input[name="age"]');
    const emailField = form.querySelector('input[name="email"]');
    const phoneField = form.querySelector('input[name="phone_number"]');
    const timezoneField = form.querySelector('select[name="timezone"]');

    if (firstNameField) firstNameField.value = initialValues.firstName;
    if (lastNameField) lastNameField.value = initialValues.lastName;
    if (ageField) ageField.value = initialValues.age;
    if (emailField) emailField.value = initialValues.email;
    if (phoneField) phoneField.value = initialValues.phone;
    if (timezoneField) timezoneField.value = initialValues.timezone;

    setEditMode(false);
  });
});
