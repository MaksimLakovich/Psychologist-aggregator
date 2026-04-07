/**
 * Скрипт страницы редактирования профиля специалиста.
 *
 * Что он делает:
 * 1) Переключает вкладки внутри одной большой формы, чтобы страница не выглядела перегруженной.
 * 2) Позволяет добавлять и скрывать карточки образования без ручного копирования HTML.
 * 3) Не трогает серверную логику: источник истины по данным остается в Django view/forms.
 */

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initEducationFormset();
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

  const activeButton = buttons.find((button) => button.classList.contains("tab-button-active")) || buttons[0];
  activateTab(activeButton.dataset.tabButton);
}

function initEducationFormset() {
  const addButton = document.querySelector("[data-add-education-form]");
  const list = document.querySelector("[data-education-formset-list]");
  const template = document.getElementById("education-empty-form-template");
  const totalFormsInput = document.getElementById("id_education-TOTAL_FORMS");

  if (!addButton || !list || !template || !totalFormsInput) return;

  addButton.addEventListener("click", () => {
    const nextIndex = Number(totalFormsInput.value);
    const html = template.innerHTML.replace(/__prefix__/g, String(nextIndex));
    list.insertAdjacentHTML("beforeend", html);
    totalFormsInput.value = String(nextIndex + 1);
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
