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

  const toggleButtons = Array.from(form.querySelectorAll("[data-profile-edit-toggle]"));
  const cancelButtons = Array.from(form.querySelectorAll("[data-profile-edit-cancel]"));
  const editActionGroups = Array.from(form.querySelectorAll("[data-profile-edit-actions]"));
  const displayActionGroups = Array.from(form.querySelectorAll("[data-profile-display-actions]"));
  const addEducationButton = document.getElementById("education-add-button");
  const activeTabInput = document.getElementById("active-profile-tab-input");
  const hasErrors = form.dataset.hasErrors === "1";
  const activeTab = form.dataset.activeTab || "profile";
  const shouldStartInProfileEditMode = hasErrors && activeTab !== "education";

  const editableInputs = Array.from(
    form.querySelectorAll(
      '[data-tab-panel="profile"] [data-editable-field="1"], [data-tab-panel="personal"] [data-editable-field="1"]',
    ),
  );
  const editableChoiceInputs = Array.from(form.querySelectorAll('[data-tab-panel="profile"] .choice-card input'));
  const editableModalCheckboxes = Array.from(
    form.querySelectorAll(".psychologist-topic-checkbox, .psychologist-method-checkbox, .psychologist-specialisation-checkbox"),
  );
  const expertiseEditButtons = Array.from(form.querySelectorAll("[data-expertise-edit-button]"));

  const modalConfigs = {
    "psychologist-topics-modal": {
      modalId: "psychologist-topics-modal",
      saveButtonId: "save-psychologist-topics-button",
      errorId: "psychologist-topics-modal-error",
      checkboxSelector: ".psychologist-topic-checkbox",
      containerId: "selected-topics-container",
      badgeClassName: "selection-badge topic-badge",
      emptyText: "Темы пока не выбраны",
    },
    "psychologist-methods-modal": {
      modalId: "psychologist-methods-modal",
      saveButtonId: "save-psychologist-methods-button",
      errorId: "psychologist-methods-modal-error",
      checkboxSelector: ".psychologist-method-checkbox",
      containerId: "selected-methods-container",
      badgeClassName: "selection-badge method-badge",
      emptyText: "Методы пока не выбраны",
    },
    "psychologist-specialisations-modal": {
      modalId: "psychologist-specialisations-modal",
      saveButtonId: "save-psychologist-specialisations-button",
      errorId: "psychologist-specialisations-modal-error",
      checkboxSelector: ".psychologist-specialisation-checkbox",
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
   * Перед отправкой формы временно снимаем disabled у полей,
   * иначе браузер просто не включит их в POST и сервер воспримет это как "пустые данные".
   */
  function enableDisabledFieldsForSubmit() {
    form.querySelectorAll(":disabled").forEach((field) => {
      if (field.name) {
        field.disabled = false;
      }
    });
  }

  /**
   * Переключает весь экран профиля между двумя состояниями:
   * - пользователь только просматривает данные;
   * - пользователь действительно редактирует профиль.
   *
   * Дополнительно метод управляет кнопками и действиями на странице:
   * - показывает "Редактировать профиль" или "Сохранить изменения / Отмена";
   * - разрешает или запрещает менять темы, методы, фото и другие поля.
   */
  function setEditMode(isEditing) {
    form.dataset.editMode = isEditing ? "1" : "0";

    editableInputs.forEach((field) => setFieldState(field, isEditing));
    editableChoiceInputs.forEach((field) => {
      field.disabled = !isEditing;
    });
    editableModalCheckboxes.forEach((field) => {
      field.disabled = !isEditing;
    });

    expertiseEditButtons.forEach((button) => {
      button.classList.toggle("hidden", !isEditing);
      button.classList.toggle("flex", isEditing);
    });

    if (isEditing) {
      editActionGroups.forEach((group) => group.classList.remove("hidden"));
      displayActionGroups.forEach((group) => group.classList.add("hidden"));
    } else {
      editActionGroups.forEach((group) => group.classList.add("hidden"));
      displayActionGroups.forEach((group) => group.classList.remove("hidden"));
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
    const emptyState = document.querySelector("[data-education-empty-state]");
    const initialEducationCardValues = new WeakMap();

    if (!list || !template || !totalFormsInput || !addEducationButton) return;

    function getEducationCards() {
      return Array.from(list.querySelectorAll("[data-education-card]"));
    }

    function getCardEditableFields(card) {
      return Array.from(card.querySelectorAll("[data-editable-field='1']"));
    }

    function getCardClearCheckboxes(card) {
      return Array.from(card.querySelectorAll('input[type="checkbox"][name$="-clear"]'));
    }

    function syncEducationEmptyState() {
      if (!emptyState) return;
      const hasVisibleCards = getEducationCards().some((card) => !card.classList.contains("hidden"));
      emptyState.classList.toggle("hidden", hasVisibleCards);
    }

    function captureEducationCardValues(card) {
      const snapshot = {};
      card.querySelectorAll("input, select, textarea").forEach((field) => {
        const key = field.name || field.id;
        if (!key) return;

        snapshot[key] = {
          value: field.type === "file" ? "" : field.value,
          checked: field.checked,
        };
      });
      initialEducationCardValues.set(card, snapshot);
    }

    function restoreEducationCardValues(card) {
      const snapshot = initialEducationCardValues.get(card);
      if (!snapshot) return;

      card.querySelectorAll("input, select, textarea").forEach((field) => {
        const key = field.name || field.id;
        const savedState = key ? snapshot[key] : null;
        if (!savedState) return;

        if (field.type === "file") {
          field.value = "";
          return;
        }

        if (field.type === "checkbox" || field.type === "radio") {
          field.checked = Boolean(savedState.checked);
          return;
        }

        field.value = savedState.value ?? "";
      });
    }

    function setEducationCardEditState(card, isEditing) {
      card.dataset.educationEditing = isEditing ? "1" : "0";

      getCardEditableFields(card).forEach((field) => setFieldState(field, isEditing));
      getCardClearCheckboxes(card).forEach((field) => {
        field.disabled = !isEditing;
      });
    }

    function getEditingEducationCard(excludedCard = null) {
      return getEducationCards().find(
        (card) => card !== excludedCard && !card.classList.contains("hidden") && card.dataset.educationEditing === "1",
      );
    }

    function focusEducationCard(card) {
      const firstField = getCardEditableFields(card).find((field) => !field.disabled && field.type !== "hidden");
      if (firstField) {
        firstField.focus({ preventScroll: true });
      }
      card.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function hideEducationCard(card) {
      const deleteCheckbox = card.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (deleteCheckbox) {
        deleteCheckbox.checked = true;
      }

      setEducationCardEditState(card, false);
      card.classList.add("hidden");
      syncEducationEmptyState();
    }

    function cancelEducationCardEditing(card) {
      if (card.dataset.educationExisting !== "1") {
        hideEducationCard(card);
        return;
      }

      restoreEducationCardValues(card);
      setEducationCardEditState(card, false);
    }

    function openEducationCardForEditing(card) {
      if (!card || card.classList.contains("hidden")) return;
      if (card.dataset.educationEditing === "1") {
        focusEducationCard(card);
        return;
      }

      const editingCard = getEditingEducationCard(card);
      if (editingCard) {
        focusEducationCard(editingCard);
        return;
      }

      setEducationCardEditState(card, true);
      focusEducationCard(card);
    }

    addEducationButton.addEventListener("click", () => {
      const editingCard = getEditingEducationCard();
      if (editingCard) {
        focusEducationCard(editingCard);
        return;
      }

      const nextIndex = Number(totalFormsInput.value);
      const html = template.innerHTML.replace(/__prefix__/g, String(nextIndex));
      list.insertAdjacentHTML("afterbegin", html);
      totalFormsInput.value = String(nextIndex + 1);

      const newCard = list.firstElementChild;
      if (!newCard) return;

      captureEducationCardValues(newCard);
      setEducationCardEditState(newCard, true);
      syncEducationEmptyState();
      focusEducationCard(newCard);
    });

    list.addEventListener("click", (event) => {
      const editButton = event.target.closest("[data-education-edit-button]");
      if (editButton) {
        openEducationCardForEditing(editButton.closest("[data-education-card]"));
        return;
      }

      const cancelButton = event.target.closest("[data-education-cancel-button]");
      if (cancelButton) {
        cancelEducationCardEditing(cancelButton.closest("[data-education-card]"));
        return;
      }

      const removeButton = event.target.closest("[data-remove-education-form]");
      if (!removeButton) return;

      const card = removeButton.closest("[data-education-card]");
      if (!card) return;

      hideEducationCard(card);
    });

    getEducationCards().forEach((card) => {
      captureEducationCardValues(card);
      setEducationCardEditState(card, card.dataset.educationEditing === "1");
    });
    syncEducationEmptyState();
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
      if (activeTabInput) {
        activeTabInput.value = tabName;
      }

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
    syncModalChoiceVisualState();
  }

  /**
   * Явно синхронизирует визуальное состояние карточек в модалках с реальным состоянием чекбоксов.
   * Это защита от браузерных и CSS-особенностей: даже если нативный чекбокс выглядит неочевидно,
   * пользователь все равно сразу видит, какие значения сейчас выбраны.
   */
  function syncModalChoiceVisualState() {
    form.querySelectorAll(".psychologist-modal-choice").forEach((choice) => {
      const checkbox = choice.querySelector(
        ".psychologist-topic-checkbox, .psychologist-method-checkbox, .psychologist-specialisation-checkbox",
      );
      if (!checkbox) return;

      choice.classList.toggle("is-selected", checkbox.checked);
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

    const savedValues = modalState.has(modalId)
      ? modalState.get(modalId)
      : readCheckedValues(modalConfig.checkboxSelector);
    applyCheckedValues(modalConfig.checkboxSelector, savedValues || []);
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

    if (restoreSavedState && modalState.has(modalId)) {
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

  // Стартовое состояние модалок нужно зафиксировать до первого setEditMode(false),
  // потому что тот вызывает closeAllModals() и раньше обнулял чекбоксы до пустого выбора.
  Object.values(modalConfigs).forEach((modalConfig) => {
    modalState.set(modalConfig.modalId, readCheckedValues(modalConfig.checkboxSelector));
  });

  applySkipIntroAnimationsIfNeeded();
  setEditMode(shouldStartInProfileEditMode);
  initEducationFormset();
  syncModalChoiceVisualState();

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

    modal.addEventListener("change", (event) => {
      if (
        event.target.matches(
          ".psychologist-topic-checkbox, .psychologist-method-checkbox, .psychologist-specialisation-checkbox",
        )
      ) {
        syncModalChoiceVisualState();
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
    enableDisabledFieldsForSubmit();
    markSkipIntroAnimationsOnce();
  });

  toggleButtons.forEach((button) => {
    button.addEventListener("click", function () {
      setEditMode(true);
    });
  });

  cancelButtons.forEach((button) => {
    button.addEventListener("click", function () {
      markSkipIntroAnimationsOnce();

      const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      if (hasErrors) {
        window.location.replace(currentUrl);
        return;
      }

      window.location.assign(currentUrl);
    });
  });
});
