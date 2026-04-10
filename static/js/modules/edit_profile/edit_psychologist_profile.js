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
  const activeTab = form.dataset.activeTab || "profile";

  const editableInputs = Array.from(form.querySelectorAll("[data-editable-field='1']"));
  const editableChoiceInputs = Array.from(form.querySelectorAll(".choice-card input"));
  const removeEducationButtons = Array.from(form.querySelectorAll("[data-remove-education-form]"));
  const expertiseEditButtons = Array.from(form.querySelectorAll("[data-expertise-edit-button]"));

  const modalConfigs = {
    "topics-modal": {
      modalId: "topics-modal",
      saveButtonId: "save-topics-button",
      errorId: "topics-modal-error",
      checkboxSelector: ".topic-checkbox",
      containerId: "selected-topics-container",
      badgeClassName: "selection-badge topic-badge",
      emptyText: "Темы пока не выбраны",
    },
    "methods-modal": {
      modalId: "methods-modal",
      saveButtonId: "save-methods-button",
      errorId: "methods-modal-error",
      checkboxSelector: ".method-checkbox",
      containerId: "selected-methods-container",
      badgeClassName: "selection-badge method-badge",
      emptyText: "Методы пока не выбраны",
    },
    "specialisations-modal": {
      modalId: "specialisations-modal",
      saveButtonId: "save-specialisations-button",
      errorId: "specialisations-modal-error",
      checkboxSelector: ".specialisation-checkbox",
      containerId: "selected-specialisations-container",
      badgeClassName: "selection-badge specialisation-badge",
      emptyText: "Специализации пока не выбраны",
    },
  };

  const modalState = new Map();
  const openButtons = document.querySelectorAll("[data-modal-open]");
  const modals = document.querySelectorAll("[data-modal]");

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
      button.classList.toggle("inline-flex", isEditing);
    });

    expertiseEditButtons.forEach((button) => {
      button.classList.toggle("hidden", !isEditing);
      button.classList.toggle("flex", isEditing);
    });

    if (isEditing) {
      editActions.classList.remove("hidden");
      displayActions.classList.add("hidden");
    } else {
      editActions.classList.add("hidden");
      displayActions.classList.remove("hidden");
      closeAllModals();
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
   * - пустая форма больше не показывается заранее.
   * - Новая карточка появляется только тогда, когда специалист явно нажимает "Добавить еще".
   */
  function initEducationFormset() {
    const list = document.querySelector("[data-education-formset-list]");
    const template = document.getElementById("education-empty-form-template");
    const totalFormsInput = document.getElementById("id_education-TOTAL_FORMS");

    if (!list || !template || !totalFormsInput || !addEducationButton) return;

    addEducationButton.addEventListener("click", () => {
      if (form.dataset.editMode !== "1") {
        setEditMode(true);
      }

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

  /**
   * Возвращает настройки конкретной модалки по ее `id`.
   * Это нужно, чтобы вся общая логика открытия, закрытия и обновления бейджей
   * работала одинаково для тем, методов и специализаций без дублирования кода.
   */
  function getModalConfigById(modalId) {
    return modalConfigs[modalId] || null;
  }

  /**
   * Читает список выбранных значений из чекбоксов внутри конкретной модалки.
   * По сути это ответ на вопрос: что сейчас отмечено пользователем в окне выбора.
   */
  function readCheckedValues(checkboxSelector) {
    return Array.from(document.querySelectorAll(`${checkboxSelector}:checked`)).map((checkbox) => checkbox.value);
  }

  /**
   * Возвращает все чекбоксы нужной модалки.
   * Этот помощник нужен, когда надо массово восстановить или обновить состояние выбора.
   */
  function getCheckboxes(checkboxSelector) {
    return Array.from(document.querySelectorAll(checkboxSelector));
  }

  /**
   * Восстанавливает чекбоксы в то состояние, которое сейчас считается "актуальным" для страницы.
   * Это важно, когда пользователь открыл модалку, что-то пощелкал и закрыл окно без применения:
   * при следующем открытии он должен увидеть не случайный промежуточный выбор, а последнее подтвержденное состояние.
   */
  function applyCheckedValues(checkboxSelector, values) {
    const valuesSet = new Set(values);
    getCheckboxes(checkboxSelector).forEach((checkbox) => {
      checkbox.checked = valuesSet.has(checkbox.value);
    });
  }

  /**
   * Очищает текст ошибки внутри модалки.
   * Пользователь не должен видеть старое сообщение об ошибке при каждом новом открытии окна.
   */
  function clearModalError(errorElement) {
    if (!errorElement) return;
    errorElement.textContent = "";
    errorElement.classList.add("hidden");
  }

  /**
   * Показывает сообщение об ошибке прямо внутри модального окна.
   * Это нужно, чтобы пользователь понимал, что именно пошло не так, не теряя контекст текущего выбора.
   */
  function showModalError(errorElement, message) {
    if (!errorElement) return;
    errorElement.textContent = message;
    errorElement.classList.remove("hidden");
  }

  /**
   * Перерисовывает бейджи на карточках после нажатия "Применить" в модалке.
   *
   * Важно: это пока только обновление интерфейса текущей страницы.
   * Реальное сохранение в БД произойдет после общего сохранения профиля.
   */
  function renderBadges(containerId, labels, badgeClassName, emptyText) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = "";

    if (!labels.length) {
      const emptyState = document.createElement("span");
      emptyState.className = "text-sm text-zinc-500";
      emptyState.textContent = emptyText;
      container.appendChild(emptyState);
      return;
    }

    labels.forEach((label) => {
      const badge = document.createElement("span");
      badge.className = badgeClassName;
      badge.textContent = label;
      container.appendChild(badge);
    });
  }

  /**
   * Собирает подписи выбранных элементов.
   * Они нужны не для отправки на сервер, а для красивого обновления карточек на самой странице:
   * вместо внутренних ID пользователь сразу видит понятные названия тем, методов и специализаций.
   */
  function collectSelectedLabels(checkboxSelector) {
    return Array.from(document.querySelectorAll(`${checkboxSelector}:checked`))
      .map((checkbox) => checkbox.dataset.label || "")
      .filter(Boolean);
  }

  /**
   * Управляет блокировкой прокрутки основного экрана, пока открыта хотя бы одна модалка.
   * Это делает взаимодействие с окном выбора спокойнее и не дает странице "уезжать" на фоне.
   */
  function syncBodyScrollLock() {
    const hasOpenedModal = Array.from(modals).some((modal) => !modal.classList.contains("hidden"));
    document.body.classList.toggle("overflow-hidden", hasOpenedModal);
  }

  /**
   * Открывает нужную модалку только в режиме редактирования.
   * Перед открытием система возвращает в чекбоксах последнее подтвержденное состояние,
   * чтобы пользователь всегда начинал работу с понятной и ожидаемой точки.
   */
  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    const modalConfig = getModalConfigById(modalId);
    if (!modal || !modalConfig || form.dataset.editMode !== "1") return;

    applyCheckedValues(modalConfig.checkboxSelector, modalState.get(modalId) || []);
    clearModalError(document.getElementById(modalConfig.errorId));
    modal.classList.remove("hidden");
    syncBodyScrollLock();
  }

  /**
   * Закрывает модалку и при необходимости откатывает несохраненный выбор.
   * Если пользователь просто закрыл окно, мы возвращаем предыдущее состояние.
   * Если он нажал "Сохранить" внутри модалки, откат уже не нужен.
   */
  function closeModal(modalId, { restoreSavedState = true } = {}) {
    const modal = document.getElementById(modalId);
    const modalConfig = getModalConfigById(modalId);
    if (!modal || !modalConfig) return;

    if (restoreSavedState) {
      applyCheckedValues(modalConfig.checkboxSelector, modalState.get(modalId) || []);
    }

    clearModalError(document.getElementById(modalConfig.errorId));
    modal.classList.add("hidden");
    syncBodyScrollLock();
  }

  /**
   * Закрывает сразу все модалки на странице.
   * Это используется, например, когда пользователь выходит из режима редактирования,
   * чтобы на экране не оставались случайно открытые окна выбора.
   */
  function closeAllModals() {
    Object.keys(modalConfigs).forEach((modalId) => closeModal(modalId));
  }

  /**
   * Локально "сохраняет" выбор модалки на самой странице:
   * - фиксирует выбранные чекбоксы как текущее состояние окна;
   * - обновляет карточки с бейджами;
   * - закрывает модалку.
   *
   * В БД эти данные уйдут только после общего submit формы профиля.
   */
  function applyModalSelection(modalId) {
    const modalConfig = getModalConfigById(modalId);
    if (!modalConfig) return;

    const selectedValues = readCheckedValues(modalConfig.checkboxSelector);
    const selectedLabels = collectSelectedLabels(modalConfig.checkboxSelector);

    modalState.set(modalId, selectedValues);
    renderBadges(
      modalConfig.containerId,
      selectedLabels,
      modalConfig.badgeClassName,
      modalConfig.emptyText,
    );
    closeModal(modalId, { restoreSavedState: false });
  }

  applySkipIntroAnimationsIfNeeded();
  setEditMode(hasErrors);
  initEducationFormset();

  // При первой загрузке страницы запоминаем текущее состояние чекбоксов в каждой модалке.
  // Это становится "точкой возврата", если пользователь откроет окно и закроет его без применения.
  Object.values(modalConfigs).forEach((modalConfig) => {
    modalState.set(modalConfig.modalId, readCheckedValues(modalConfig.checkboxSelector));
  });

  // Кнопки-иконки на карточках открывают соответствующие модальные окна выбора.
  openButtons.forEach((button) => {
    button.addEventListener("click", () => {
      openModal(button.dataset.modalOpen);
    });
  });

  // Каждая модалка закрывается по своей кнопке-крестику/кнопке "Отмена"
  // и по клику на затемненный фон вокруг окна.
  modals.forEach((modal) => {
    modal.querySelectorAll("[data-modal-close]").forEach((button) => {
      button.addEventListener("click", () => {
        closeModal(modal.id);
      });
    });

    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeModal(modal.id);
      }
    });
  });

  // Клавиша Escape закрывает только текущее открытое окно, не затрагивая остальные данные формы.
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;

    const openedModal = Array.from(modals).find((modal) => !modal.classList.contains("hidden"));
    if (openedModal) {
      closeModal(openedModal.id);
    }
  });

  // Кнопка "Сохранить" внутри каждой модалки пока обновляет только сам экран,
  // а не отправляет отдельный запрос на сервер: реальное сохранение происходит общим submit формы профиля.
  Object.values(modalConfigs).forEach((modalConfig) => {
    document.getElementById(modalConfig.saveButtonId)?.addEventListener("click", () => {
      applyModalSelection(modalConfig.modalId);
    });
  });
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
