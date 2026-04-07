/**
 * Скрипт управляет режимами просмотра/редактирования страницы профиля специалиста.
 *
 * Логика близка к клиентскому профилю, но с поправкой на более сложный экран:
 * 1) При загрузке страница открывается в режиме просмотра.
 * 2) После нажатия "Редактировать профиль" доступные поля становятся активными.
 * 3) Появляются кнопки "Сохранить изменения" и "Отмена".
 * 4) "Отмена" не сохраняет данные и возвращает экран к исходному состоянию через перезагрузку GET-страницы.
 */

document.addEventListener("DOMContentLoaded", function () {
  // Одноразовый флаг: если пользователь только что сохранял профиль или отменял изменения,
  // на следующем открытии не запускаем заново вступительные анимации.
  // Это делает экран спокойнее и убирает ощущение "прыгающего" интерфейса
  const SKIP_INTRO_ANIMATIONS_ONCE_KEY = "psychologistProfileEditSkipIntroAnimationsOnce";

  const form = document.getElementById("psychologist-profile-form");
  if (!form) return;

  const toggleBtn = document.getElementById("profile-edit-toggle");
  const cancelBtn = document.getElementById("profile-edit-cancel");
  const editActions = document.getElementById("profile-edit-actions");
  const displayActions = document.getElementById("display-actions");
  const addEducationButton = document.getElementById("education-add-button");
  const hasErrors = form.dataset.hasErrors === "1";
  const activeTab = form.dataset.activeTab || "personal";

  const editableInputs = Array.from(form.querySelectorAll("[data-editable-field='1']"));
  const editableChoiceInputs = Array.from(form.querySelectorAll(".choice-card input"));
  const removeEducationButtons = Array.from(form.querySelectorAll("[data-remove-education-form]"));

  initTabs(activeTab);

  /**
   * Если до этого пользователь уже взаимодействовал со страницей, убираем повторный показ анимаций.
   * Смысл: при обычной работе с профилем пользователь часто нажимает "Сохранить" или "Отмена".
   * Если после каждого такого действия снова запускать все анимации, экран выглядит менее стабильным.
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

    sessionStorage.removeItem(SKIP_INTRO_ANIMATIONS_ONCE_KEY);
  }

  /**
   * Помечаем, что при следующей загрузке страницы вступительные анимации нужно пропустить.
   * Это не меняет данные профиля, а только делает поведение интерфейса аккуратнее после сохранения или отмены действий
   */
  function markSkipIntroAnimationsOnce() {
    sessionStorage.setItem(SKIP_INTRO_ANIMATIONS_ONCE_KEY, "1");
  }

  /**
   * Переключает отдельное поле между режимами "просмотр" и "редактирование".
   * Суть:
   * - в режиме просмотра поле должно выглядеть как закрытое для изменения;
   * - в режиме редактирования то же поле становится активным и получает рабочий стиль формы.
   */
  function setFieldState(field, isEditing) {
    const viewClasses = field.dataset.viewClass || field.className;
    const editClasses = field.dataset.editClass || field.className;

    if (isEditing) {
      field.className = editClasses;
      field.disabled = false;
      if (field.type !== "checkbox" && field.type !== "file") {
        field.removeAttribute("readonly");
      }
      return;
    }

    field.className = viewClasses;
    if (field.tagName === "SELECT" || field.type === "checkbox" || field.type === "file") {
      field.disabled = true;
    } else {
      field.setAttribute("readonly", "readonly");
    }
  }

  /**
   * Переключает весь экран профиля между двумя состояниями:
   * - пользователь только просматривает данные;
   * - пользователь действительно редактирует профиль.
   *
   * Дополнительно метод управляет кнопками и действиями на странице:
   * - показывает "Редактировать профиль" или "Сохранить изменения / Отмена";
   * - открывает или скрывает удаление карточек образования;
   * - разрешает или запрещает менять темы, методы, фото и другие поля.
   */
  function setEditMode(isEditing) {
    form.dataset.editMode = isEditing ? "1" : "0";

    editableInputs.forEach((field) => setFieldState(field, isEditing));
    editableChoiceInputs.forEach((field) => {
      field.disabled = !isEditing;
    });

    removeEducationButtons.forEach((button) => {
      button.classList.toggle("hidden", !isEditing);
    });

    if (addEducationButton) {
      addEducationButton.classList.toggle("hidden", !isEditing);
      addEducationButton.classList.toggle("inline-flex", isEditing);
    }

    if (isEditing) {
      editActions.classList.remove("hidden");
      displayActions.classList.add("hidden");
    } else {
      editActions.classList.add("hidden");
      displayActions.classList.remove("hidden");
    }
  }

  /**
   * Настраивает работу блока "Образование".
   *
   * Смысл:
   * у специалиста может быть несколько записей об обучении, поэтому пользователь должен уметь прямо на странице:
   * - добавить новую карточку образования;
   * - убрать ненужную карточку;
   * - при этом сервер должен получить корректную структуру formset.
   */
  function initEducationFormset() {
    const list = document.querySelector("[data-education-formset-list]");
    const template = document.getElementById("education-empty-form-template");
    const totalFormsInput = document.getElementById("id_education-TOTAL_FORMS");

    if (!list || !template || !totalFormsInput || !addEducationButton) return;

    addEducationButton.addEventListener("click", () => {
      const nextIndex = Number(totalFormsInput.value);
      const html = template.innerHTML.replace(/__prefix__/g, String(nextIndex));
      list.insertAdjacentHTML("beforeend", html);
      totalFormsInput.value = String(nextIndex + 1);

      const newCard = list.lastElementChild;
      if (!newCard) return;

      newCard.querySelectorAll("[data-editable-field='1']").forEach((field) => setFieldState(field, true));
      const removeButton = newCard.querySelector("[data-remove-education-form]");
      if (removeButton) {
        removeButton.classList.remove("hidden");
        removeButton.classList.add("inline-flex");
      }
    });

    list.addEventListener("click", (event) => {
      const removeButton = event.target.closest("[data-remove-education-form]");
      if (!removeButton) return;

      const card = removeButton.closest("[data-education-card]");
      if (!card) return;

      const deleteCheckbox = card.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (deleteCheckbox) {
        deleteCheckbox.checked = true;
      }

      card.classList.add("hidden");
    });
  }

  /**
   * Настраивает переключение вкладок на странице профиля.
   *
   * Это нужно, чтобы большой экран с множеством данных оставался понятным:
   * - личные данные;
   * - образование;
   * - темы и методы.
   *
   * Метод также умеет открыть нужную вкладку сразу после ответа сервера, если именно в этом блоке произошла ошибка.
   */
  function initTabs(initialTab) {
    const buttons = Array.from(document.querySelectorAll("[data-tab-button]"));
    const panels = Array.from(document.querySelectorAll("[data-tab-panel]"));
    if (!buttons.length || !panels.length) return;

    function activateTab(tabName) {
      buttons.forEach((button) => {
        const isActive = button.dataset.tabButton === tabName;
        button.classList.toggle("tab-button-active", isActive);
        button.classList.toggle("text-zinc-500", !isActive);
      });

      panels.forEach((panel) => {
        panel.classList.toggle("hidden", panel.dataset.tabPanel !== tabName);
      });
    }

    buttons.forEach((button) => {
      button.addEventListener("click", () => activateTab(button.dataset.tabButton));
    });

    activateTab(initialTab);
  }

  applySkipIntroAnimationsIfNeeded();
  setEditMode(hasErrors);
  initEducationFormset();

  // После нажатия "Сохранить" не хотим заново проигрывать все стартовые анимации.
  form.addEventListener("submit", function () {
    markSkipIntroAnimationsOnce();
  });

  if (toggleBtn) {
    // Пользователь явно решил перейти из режима просмотра в режим редактирования.
    toggleBtn.addEventListener("click", function () {
      setEditMode(true);
    });
  }

  if (cancelBtn) {
    // "Отмена" не пытается вручную откатывать десятки полей на клиенте.
    // Вместо этого мы возвращаем страницу к чистому состоянию через повторное открытие GET-версии экрана.
    // Это надежнее для большого профиля с несколькими блоками и formset.
    cancelBtn.addEventListener("click", function () {
      markSkipIntroAnimationsOnce();

      const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      if (hasErrors) {
        window.location.replace(currentUrl);
        return;
      }

      window.location.assign(currentUrl);
    });
  }
});
