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

    if (!isOverride) {
      overrideFields.forEach((field) => {
        const input = field.querySelector("input, select, textarea");
        if (input) input.value = "";
      });
    }
  }

  select.addEventListener("change", syncVisibility);
  syncVisibility();
}
