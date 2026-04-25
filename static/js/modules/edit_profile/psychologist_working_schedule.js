/**
 * Скрипт страницы рабочего расписания специалиста.
 *
 * На странице две разные формы, но логика поведения похожа:
 * 1) вкладки помогают не смешивать базовое правило и исключения;
 * 2) formset-строки позволяют добавлять рабочие окна прямо в интерфейсе;
 * 3) для исключения типа "override" показываем только релевантные поля.
 */

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initRuleEditMode();
  initWindowFormset({
    addButtonSelector: '[data-add-window-form="rule"]',
    listSelector: '[data-window-formset-list="rule"]',
    totalFormsInputId: "id_rule_windows-TOTAL_FORMS",
    templateId: "rule-window-empty-form-template",
  });
  initWindowFormset({
    addButtonSelector: '[data-add-window-form="exception"]',
    listSelector: '[data-window-formset-list="exception"]',
    totalFormsInputId: "id_exception_windows-TOTAL_FORMS",
    templateId: "exception-window-empty-form-template",
  });
  initExceptionTypeToggle();
});

function initRuleEditMode() {
  const form = document.querySelector("[data-rule-form-root]");
  const editButton = document.querySelector("[data-edit-rule-button]");
  const createButton = document.querySelector("[data-create-rule-button]");
  const cancelButton = document.querySelector("[data-cancel-rule-edit]");
  const emptyState = document.querySelector("[data-rule-empty-state]");
  const editOnlyElements = Array.from(document.querySelectorAll("[data-rule-edit-visible]"));
  const readonlyOnlyElements = Array.from(document.querySelectorAll("[data-rule-readonly-visible]"));

  if (!form) return;

  const startsReadonly = form.dataset.ruleReadonlyInitial === "true";
  const editableFields = Array.from(form.querySelectorAll("input, select, textarea, button")).filter((field) => {
    return field.type !== "hidden";
  });

  function setEditingMode(isEditing) {
    // Пока специалист не нажал "Редактировать", форма показывает текущие значения как справочную карточку.
    form.classList.toggle("working-schedule-readonly", startsReadonly && !isEditing);

    if (editButton) {
      editButton.classList.toggle("hidden", isEditing);
    }

    editOnlyElements.forEach((element) => {
      element.classList.toggle("hidden", !isEditing);
    });

    readonlyOnlyElements.forEach((element) => {
      element.classList.toggle("hidden", isEditing);
    });

    editableFields.forEach((field) => {
      field.disabled = startsReadonly && !isEditing;
    });
  }

  if (editButton) {
    editButton.addEventListener("click", () => setEditingMode(true));
  }

  if (createButton) {
    createButton.addEventListener("click", () => {
      // Когда графика еще нет, сначала показываем объясняющий блок, а форму открываем по явному действию
      emptyState?.classList.add("hidden");
      form.classList.remove("hidden");
    });
  }

  if (cancelButton) {
    cancelButton.addEventListener("click", () => {
      window.location.href = `${window.location.pathname}${window.location.search}`;
    });
  }

  setEditingMode(!startsReadonly);
}

function initTabs() {
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

  const initiallyVisiblePanel = panels.find((panel) => !panel.classList.contains("hidden"));
  activateTab(initiallyVisiblePanel?.dataset.tabPanel || buttons[0].dataset.tabButton);
}

function initWindowFormset({ addButtonSelector, listSelector, totalFormsInputId, templateId }) {
  const addButton = document.querySelector(addButtonSelector);
  const list = document.querySelector(listSelector);
  const template = document.getElementById(templateId);
  const totalFormsInput = document.getElementById(totalFormsInputId);

  if (!addButton || !list || !template || !totalFormsInput) return;

  addButton.addEventListener("click", () => {
    const nextIndex = Number(totalFormsInput.value);
    const html = template.innerHTML.replace(/__prefix__/g, String(nextIndex));
    list.insertAdjacentHTML("beforeend", html);
    totalFormsInput.value = String(nextIndex + 1);
  });

  list.addEventListener("click", (event) => {
    const removeButton = event.target.closest("[data-remove-window-form]");
    if (!removeButton) return;

    const card = removeButton.closest("[data-window-card]");
    if (!card) return;

    const deleteCheckbox = card.querySelector('input[type="checkbox"][name$="-DELETE"]');
    if (deleteCheckbox) {
      deleteCheckbox.checked = true;
    }

    card.classList.add("hidden");
  });
}

function initExceptionTypeToggle() {
  const select = document.querySelector('[data-exception-type-select="1"]');
  const overrideSection = document.querySelector("[data-override-window-section]");
  const overrideFields = Array.from(document.querySelectorAll("[data-override-config-field]"));

  if (!select || !overrideSection) return;

  function syncVisibility() {
    const isOverride = select.value === "override";
    overrideSection.classList.toggle("hidden", !isOverride);
    overrideFields.forEach((field) => field.classList.toggle("hidden", !isOverride));
  }

  select.addEventListener("change", syncVisibility);
  syncVisibility();
}
