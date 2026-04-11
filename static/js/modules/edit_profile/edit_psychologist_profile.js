/**
 * Скрипт управляет экраном редактирования профиля специалиста.
 *
 * Здесь есть 4 самостоятельных сценария:
 * 1) переключение вкладок;
 * 2) общий режим редактирования для вкладок "Данные профиля" и "Контактные данные";
 * 3) локальное редактирование карточек образования;
 * 4) модалки для тем, методов и специализаций.
 *
 * Цель скрипта простая:
 * пользователь всегда должен видеть понятное состояние экрана,
 * не терять введенные данные и не сталкиваться с "прыгающим" интерфейсом.
 */
document.addEventListener("DOMContentLoaded", () => {
  const SKIP_INTRO_ANIMATIONS_ONCE_KEY = "psychologistProfileEditSkipIntroAnimationsOnce";

  const form = document.getElementById("psychologist-profile-form");
  if (!form) return;

  const activeTabInput = document.getElementById("active-profile-tab-input");
  const toggleButtons = Array.from(form.querySelectorAll("[data-profile-edit-toggle]"));
  const cancelButtons = Array.from(form.querySelectorAll("[data-profile-edit-cancel]"));
  const editActionGroups = Array.from(form.querySelectorAll("[data-profile-edit-actions]"));
  const displayActionGroups = Array.from(form.querySelectorAll("[data-profile-display-actions]"));
  const expertiseEditButtons = Array.from(form.querySelectorAll("[data-expertise-edit-button]"));
  const addEducationButton = document.getElementById("education-add-button");

  const hasErrors = form.dataset.hasErrors === "1";
  const initialTab = form.dataset.activeTab || "profile";
  const shouldStartInProfileEditMode = hasErrors && initialTab !== "education";

  const profileEditableFields = Array.from(
    form.querySelectorAll(
      '[data-tab-panel="profile"] [data-editable-field="1"], [data-tab-panel="personal"] [data-editable-field="1"]',
    ),
  );
  const profileChoiceInputs = Array.from(form.querySelectorAll('[data-tab-panel="profile"] .choice-card input'));
  const expertiseCheckboxes = Array.from(
    form.querySelectorAll(".psychologist-topic-checkbox, .psychologist-method-checkbox, .psychologist-specialisation-checkbox"),
  );

  const modalConfigs = {
    "psychologist-topics-modal": {
      checkboxSelector: ".psychologist-topic-checkbox",
      saveButtonId: "save-psychologist-topics-button",
      errorId: "psychologist-topics-modal-error",
      containerId: "selected-topics-container",
      badgeClassName: "selection-badge topic-badge",
      emptyText: "Темы пока не выбраны",
    },
    "psychologist-methods-modal": {
      checkboxSelector: ".psychologist-method-checkbox",
      saveButtonId: "save-psychologist-methods-button",
      errorId: "psychologist-methods-modal-error",
      containerId: "selected-methods-container",
      badgeClassName: "selection-badge method-badge",
      emptyText: "Методы пока не выбраны",
    },
    "psychologist-specialisations-modal": {
      checkboxSelector: ".psychologist-specialisation-checkbox",
      saveButtonId: "save-psychologist-specialisations-button",
      errorId: "psychologist-specialisations-modal-error",
      containerId: "selected-specialisations-container",
      badgeClassName: "selection-badge specialisation-badge",
      emptyText: "Специализации пока не выбраны",
    },
  };

  let closeAllExpertiseModals = () => {};

  /**
   * Эта функция делает экран стабильнее после сохранения или отмены.
   * Если пользователь уже работал с формой, при следующем открытии
   * мы не проигрываем заново стартовые анимации и страница выглядит спокойнее.
   */
  function applySkipIntroAnimationsIfNeeded() {
    const shouldSkip = sessionStorage.getItem(SKIP_INTRO_ANIMATIONS_ONCE_KEY) === "1";
    if (!shouldSkip) return;

    document.querySelectorAll(".animate-fade-in-up, .animate-fade-in-left").forEach((element) => {
      element.classList.remove("animate-fade-in-up", "animate-fade-in-left");
      element.style.opacity = "1";
      element.style.animation = "none";
    });

    sessionStorage.removeItem(SKIP_INTRO_ANIMATIONS_ONCE_KEY);
  }

  /**
   * Эта функция запоминает, что после текущего действия
   * стартовые анимации на следующей загрузке лучше пропустить.
   */
  function rememberSkipIntroAnimationsOnce() {
    sessionStorage.setItem(SKIP_INTRO_ANIMATIONS_ONCE_KEY, "1");
  }

  /**
   * Эта функция переключает отдельное поле между режимом "смотрю" и "редактирую".
   * Для пользователя это означает одно:
   * поле либо закрыто от изменений, либо действительно готово к вводу.
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
   * Эта функция включает все disabled-поля прямо перед submit.
   * Это техническая защита: браузер не отправляет disabled-значения в POST,
   * а значит сервер мог бы ошибочно подумать, что пользователь их очистил.
   */
  function enableDisabledFieldsForSubmit() {
    form.querySelectorAll(":disabled").forEach((field) => {
      if (field.name) {
        field.disabled = false;
      }
    });
  }

  /**
   * Эта функция управляет общим режимом редактирования профиля.
   * Она нужна только для вкладок с базовыми данными и для модалок экспертизы.
   * Блок образования живет отдельно и редактируется локально по карточкам.
   */
  function setProfileEditMode(isEditing) {
    form.dataset.editMode = isEditing ? "1" : "0";

    profileEditableFields.forEach((field) => setFieldState(field, isEditing));
    profileChoiceInputs.forEach((field) => {
      field.disabled = !isEditing;
    });
    expertiseCheckboxes.forEach((field) => {
      field.disabled = !isEditing;
    });

    expertiseEditButtons.forEach((button) => {
      button.classList.toggle("hidden", !isEditing);
      button.classList.toggle("flex", isEditing);
    });

    editActionGroups.forEach((group) => group.classList.toggle("hidden", !isEditing));
    displayActionGroups.forEach((group) => group.classList.toggle("hidden", isEditing));

    if (!isEditing) {
      closeAllExpertiseModals();
    }
  }

  /**
   * Эта функция возвращает пользователя на "чистую" GET-версию страницы.
   * Бизнес-смысл простой:
   * если человек нажал "Отмена", экран должен вернуться в исходное состояние,
   * без локальных черновиков и без следов серверных ошибок.
   */
  function reloadCurrentPage({ replaceHistory = false } = {}) {
    rememberSkipIntroAnimationsOnce();

    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (replaceHistory) {
      window.location.replace(currentUrl);
      return;
    }

    window.location.assign(currentUrl);
  }

  /**
   * Эта функция настраивает вкладки.
   * Пользователь кликает по названию блока и сразу видит именно тот раздел,
   * с которым хочет работать сейчас.
   */
  function initTabs(activeTab) {
    const buttons = Array.from(form.querySelectorAll("[data-tab-button]"));
    const panels = Array.from(form.querySelectorAll("[data-tab-panel]"));
    if (!buttons.length || !panels.length) return;

    /**
     * Эта вложенная функция включает одну конкретную вкладку.
     * Важный побочный эффект:
     * мы также записываем активную вкладку в hidden input,
     * чтобы сервер после сохранения мог вернуть пользователя туда же.
     */
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

    activateTab(activeTab);
  }

  /**
   * Эта функция настраивает блоки "Темы / Методы / Специализации".
   * Для пользователя это единый сценарий:
   * открыть модалку, увидеть текущий выбор, изменить его и применить на странице.
   */
  function initExpertiseModals() {
    const modalSelections = new Map();
    const modalElements = Array.from(document.querySelectorAll("[data-modal]"));
    const openButtons = Array.from(form.querySelectorAll("[data-modal-open]"));

    if (!modalElements.length) {
      return () => {};
    }

    /**
     * Эта вложенная функция получает настройки конкретной модалки.
     * Она нужна, чтобы темы, методы и специализации работали по одной логике.
     */
    function getModalConfig(modalId) {
      return modalConfigs[modalId] || null;
    }

    /**
     * Эта вложенная функция читает выбранные значения в конкретной модалке.
     * Грубо говоря, это ответ на вопрос:
     * "Какие пункты сейчас отмечены галочками?"
     */
    function readCheckedValues(checkboxSelector) {
      return Array.from(document.querySelectorAll(`${checkboxSelector}:checked`)).map((checkbox) => checkbox.value);
    }

    /**
     * Эта вложенная функция собирает человекочитаемые названия выбранных пунктов.
     * Именно эти подписи потом выводятся в виде бейджей на карточке вкладки.
     */
    function readCheckedLabels(checkboxSelector) {
      return Array.from(document.querySelectorAll(`${checkboxSelector}:checked`))
        .map((checkbox) => checkbox.dataset.label || "")
        .filter(Boolean);
    }

    /**
     * Эта вложенная функция визуально синхронизирует карточки внутри модалок.
     * Даже если нативный чекбокс браузера ведет себя неидеально,
     * пользователь все равно видит, какие значения сейчас активны.
     */
    function syncModalChoiceCards() {
      form.querySelectorAll(".psychologist-modal-choice").forEach((choice) => {
        const checkbox = choice.querySelector(
          ".psychologist-topic-checkbox, .psychologist-method-checkbox, .psychologist-specialisation-checkbox",
        );
        if (!checkbox) return;

        choice.classList.toggle("is-selected", checkbox.checked);
      });
    }

    /**
     * Эта вложенная функция массово выставляет галочки внутри модалки.
     * Она используется при открытии окна и при откате несохраненного выбора.
     */
    function setCheckedValues(checkboxSelector, values) {
      const valuesSet = new Set(values);
      document.querySelectorAll(checkboxSelector).forEach((checkbox) => {
        checkbox.checked = valuesSet.has(checkbox.value);
      });
      syncModalChoiceCards();
    }

    /**
     * Эта вложенная функция очищает старое сообщение об ошибке внутри модалки.
     * Пользователь не должен видеть вчерашнюю ошибку при новом открытии окна.
     */
    function clearModalError(errorElement) {
      if (!errorElement) return;
      errorElement.textContent = "";
      errorElement.classList.add("hidden");
    }

    /**
     * Эта вложенная функция перерисовывает бейджи на карточке блока.
     * База здесь еще не сохраняется:
     * пользователь просто получает понятную визуальную обратную связь на самой странице.
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
     * Эта вложенная функция включает или выключает прокрутку фона.
     * Пока открыта модалка, страница под ней не должна "уезжать".
     */
    function syncBodyScrollLock() {
      const hasOpenedModal = modalElements.some((modal) => !modal.classList.contains("hidden"));
      document.body.classList.toggle("overflow-hidden", hasOpenedModal);
    }

    /**
     * Эта вложенная функция открывает конкретную модалку.
     * Перед открытием она возвращает последний подтвержденный выбор,
     * чтобы пользователь не видел случайный промежуточный черновик.
     */
    function openModal(modalId) {
      const modal = document.getElementById(modalId);
      const modalConfig = getModalConfig(modalId);
      if (!modal || !modalConfig || form.dataset.editMode !== "1") return;

      const savedValues = modalSelections.get(modalId) || readCheckedValues(modalConfig.checkboxSelector);
      setCheckedValues(modalConfig.checkboxSelector, savedValues);
      clearModalError(document.getElementById(modalConfig.errorId));
      modal.classList.remove("hidden");
      syncBodyScrollLock();
    }

    /**
     * Эта вложенная функция закрывает конкретную модалку.
     * Если пользователь закрыл окно без применения,
     * экран возвращается к последнему подтвержденному состоянию.
     */
    function closeModal(modalId, { restoreSavedState = true } = {}) {
      const modal = document.getElementById(modalId);
      const modalConfig = getModalConfig(modalId);
      if (!modal || !modalConfig) return;

      if (restoreSavedState && modalSelections.has(modalId)) {
        setCheckedValues(modalConfig.checkboxSelector, modalSelections.get(modalId));
      }

      clearModalError(document.getElementById(modalConfig.errorId));
      modal.classList.add("hidden");
      syncBodyScrollLock();
    }

    /**
     * Эта вложенная функция закрывает все модалки сразу.
     * Она нужна, когда пользователь выходит из режима редактирования страницы.
     */
    function closeAllModals() {
      Object.keys(modalConfigs).forEach((modalId) => closeModal(modalId));
    }

    /**
     * Эта вложенная функция применяет изменения из модалки к текущему экрану.
     * Смысл для пользователя такой:
     * выбор уже виден на странице, а в БД он уйдет после общего сохранения профиля.
     */
    function applyModalSelection(modalId) {
      const modalConfig = getModalConfig(modalId);
      if (!modalConfig) return;

      const selectedValues = readCheckedValues(modalConfig.checkboxSelector);
      const selectedLabels = readCheckedLabels(modalConfig.checkboxSelector);

      modalSelections.set(modalId, selectedValues);
      renderBadges(
        modalConfig.containerId,
        selectedLabels,
        modalConfig.badgeClassName,
        modalConfig.emptyText,
      );
      closeModal(modalId, { restoreSavedState: false });
    }

    Object.entries(modalConfigs).forEach(([modalId, modalConfig]) => {
      modalSelections.set(modalId, readCheckedValues(modalConfig.checkboxSelector));
    });

    syncModalChoiceCards();

    openButtons.forEach((button) => {
      button.addEventListener("click", () => openModal(button.dataset.modalOpen));
    });

    modalElements.forEach((modal) => {
      modal.querySelectorAll("[data-modal-close]").forEach((button) => {
        button.addEventListener("click", () => closeModal(modal.id));
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
          syncModalChoiceCards();
        }
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;

      const openedModal = modalElements.find((modal) => !modal.classList.contains("hidden"));
      if (openedModal) {
        closeModal(openedModal.id);
      }
    });

    Object.entries(modalConfigs).forEach(([modalId, modalConfig]) => {
      document.getElementById(modalConfig.saveButtonId)?.addEventListener("click", () => {
        applyModalSelection(modalId);
      });
    });

    return closeAllModals;
  }

  /**
   * Эта функция настраивает карточки образования.
   * В отличие от остальных вкладок здесь нет общего режима редактирования:
   * каждая карточка редактируется отдельно и не мешает соседним.
   */
  function initEducationCards() {
    const list = form.querySelector("[data-education-formset-list]");
    const template = document.getElementById("education-empty-form-template");
    const totalFormsInput = document.getElementById("id_education-TOTAL_FORMS");
    const emptyState = form.querySelector("[data-education-empty-state]");
    const savedCardState = new WeakMap();

    if (!list || !template || !totalFormsInput || !addEducationButton) return;

    /**
     * Эта вложенная функция возвращает все видимые карточки образования.
     * Она нужна как базовый список для остальных действий блока.
     */
    function getCards() {
      return Array.from(list.querySelectorAll("[data-education-card]"));
    }

    /**
     * Эта вложенная функция находит все поля, которыми реально управляет пользователь.
     * Скрытые технические поля formset сюда не входят.
     */
    function getEditableFields(card) {
      return Array.from(card.querySelectorAll("[data-editable-field='1']"));
    }

    /**
     * Эта вложенная функция находит чекбоксы "clear" у файлов.
     * Их тоже надо включать только во время редактирования карточки.
     */
    function getClearCheckboxes(card) {
      return Array.from(card.querySelectorAll('input[type="checkbox"][name$="-clear"]'));
    }

    /**
     * Эта вложенная функция показывает или скрывает пустое состояние блока.
     * Если карточек нет, пользователь должен явно видеть, что можно добавить первую запись.
     */
    function syncEmptyState() {
      if (!emptyState) return;

      const hasVisibleCards = getCards().some((card) => !card.classList.contains("hidden"));
      emptyState.classList.toggle("hidden", hasVisibleCards);
    }

    /**
     * Эта вложенная функция запоминает текущее состояние карточки.
     * Это нужно, чтобы кнопка "Отмена" возвращала пользователя
     * к последним сохраненным данным, а не к случайному промежуточному вводу.
     */
    function rememberCardValues(card) {
      const snapshot = {};

      card.querySelectorAll("input, select, textarea").forEach((field) => {
        const key = field.name || field.id;
        if (!key) return;

        snapshot[key] = {
          value: field.type === "file" ? "" : field.value,
          checked: field.checked,
        };
      });

      savedCardState.set(card, snapshot);
    }

    /**
     * Эта вложенная функция восстанавливает карточку из ранее сохраненного снимка.
     * Для пользователя это и есть поведение кнопки "Отмена".
     */
    function restoreCardValues(card) {
      const snapshot = savedCardState.get(card);
      if (!snapshot) return;

      card.querySelectorAll("input, select, textarea").forEach((field) => {
        const key = field.name || field.id;
        const savedValue = key ? snapshot[key] : null;
        if (!savedValue) return;

        if (field.type === "file") {
          field.value = "";
          return;
        }

        if (field.type === "checkbox" || field.type === "radio") {
          field.checked = Boolean(savedValue.checked);
          return;
        }

        field.value = savedValue.value ?? "";
      });
    }

    /**
     * Эта вложенная функция переводит одну карточку в режим просмотра или редактирования.
     * В этот момент включаются или выключаются поля, file-операции и action-иконки.
     */
    function setCardEditMode(card, isEditing) {
      card.dataset.educationEditing = isEditing ? "1" : "0";

      getEditableFields(card).forEach((field) => setFieldState(field, isEditing));
      getClearCheckboxes(card).forEach((checkbox) => {
        checkbox.disabled = !isEditing;
      });
    }

    /**
     * Эта вложенная функция ищет карточку, которая уже открыта на редактирование.
     * Она нужна, чтобы не допускать одновременное редактирование нескольких записей:
     * иначе экран быстро становится шумным и неочевидным.
     */
    function findEditingCard(excludedCard = null) {
      return getCards().find(
        (card) => card !== excludedCard && !card.classList.contains("hidden") && card.dataset.educationEditing === "1",
      );
    }

    /**
     * Эта вложенная функция переводит фокус на открытую карточку.
     * После добавления или включения редактирования пользователь сразу попадает туда, где должен работать.
     */
    function focusCard(card) {
      const firstEditableField = getEditableFields(card).find((field) => !field.disabled && field.type !== "hidden");
      if (firstEditableField) {
        firstEditableField.focus({ preventScroll: true });
      }
      card.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    /**
     * Эта вложенная функция скрывает карточку и отмечает ее на удаление.
     * Для существующей записи это означает удаление при следующем сохранении формы.
     * Для новой пустой карточки это означает просто убрать черновик с экрана.
     */
    function hideCard(card) {
      const deleteCheckbox = card.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (deleteCheckbox) {
        deleteCheckbox.checked = true;
      }

      setCardEditMode(card, false);
      card.classList.add("hidden");
      syncEmptyState();
    }

    /**
     * Эта вложенная функция обрабатывает "Отмену" для одной карточки.
     * Если карточка новая, мы просто убираем ее.
     * Если карточка старая, возвращаем последние запомненные значения.
     */
    function cancelCardEditing(card) {
      if (card.dataset.educationExisting !== "1") {
        hideCard(card);
        return;
      }

      restoreCardValues(card);
      setCardEditMode(card, false);
    }

    /**
     * Эта вложенная функция открывает одну карточку на редактирование.
     * Если другая карточка уже редактируется, вместо конфликта мы просто ведем пользователя к ней.
     */
    function openCardEditing(card) {
      if (!card || card.classList.contains("hidden")) return;

      if (card.dataset.educationEditing === "1") {
        focusCard(card);
        return;
      }

      const editingCard = findEditingCard(card);
      if (editingCard) {
        focusCard(editingCard);
        return;
      }

      setCardEditMode(card, true);
      focusCard(card);
    }

    /**
     * Эта вложенная функция добавляет новую карточку образования в начало списка.
     * Такое поведение экономит внимание пользователя:
     * он сразу видит новый блок наверху и не ищет его внизу страницы.
     */
    function addNewCard() {
      const editingCard = findEditingCard();
      if (editingCard) {
        focusCard(editingCard);
        return;
      }

      const nextIndex = Number(totalFormsInput.value);
      const html = template.innerHTML.replace(/__prefix__/g, String(nextIndex));
      list.insertAdjacentHTML("afterbegin", html);
      totalFormsInput.value = String(nextIndex + 1);

      const newCard = list.firstElementChild;
      if (!newCard) return;

      rememberCardValues(newCard);
      setCardEditMode(newCard, true);
      syncEmptyState();
      focusCard(newCard);
    }

    addEducationButton.addEventListener("click", addNewCard);

    list.addEventListener("click", (event) => {
      const editButton = event.target.closest("[data-education-edit-button]");
      if (editButton) {
        openCardEditing(editButton.closest("[data-education-card]"));
        return;
      }

      const cancelButton = event.target.closest("[data-education-cancel-button]");
      if (cancelButton) {
        cancelCardEditing(cancelButton.closest("[data-education-card]"));
        return;
      }

      const removeButton = event.target.closest("[data-remove-education-form]");
      if (removeButton) {
        hideCard(removeButton.closest("[data-education-card]"));
      }
    });

    getCards().forEach((card) => {
      rememberCardValues(card);
      setCardEditMode(card, card.dataset.educationEditing === "1");
    });

    syncEmptyState();
  }

  /**
   * Эта функция настраивает кнопки редактирования и отмены для вкладок профиля.
   * Она описывает ровно тот сценарий, который пользователь ожидает:
   * "войти в редактирование" и "выйти без сохранения".
   */
  function initProfileActionButtons() {
    toggleButtons.forEach((button) => {
      button.addEventListener("click", () => {
        setProfileEditMode(true);
      });
    });

    cancelButtons.forEach((button) => {
      button.addEventListener("click", () => {
        reloadCurrentPage({ replaceHistory: hasErrors });
      });
    });
  }

  closeAllExpertiseModals = initExpertiseModals();
  initTabs(initialTab);
  initEducationCards();
  initProfileActionButtons();

  applySkipIntroAnimationsIfNeeded();
  setProfileEditMode(shouldStartInProfileEditMode);

  form.addEventListener("submit", () => {
    enableDisabledFieldsForSubmit();
    rememberSkipIntroAnimationsOnce();
  });
});
