/**
 * Модуль управления аккордеоном клиентской боковой НАВИГАЦИИ.
 *
 * Принципы:
 * 1) Источник истины для активного пункта НАВИГАЦИИ находится на сервере (URL/вьюха), то есть мы его из вью передаем а не определяем в sessionStorage.
 * 2) Этот JS отвечает только за поведение групп аккордеона (открыть/закрыть).
 * 3) В один момент времени может быть открыта только одна группа.
 */

/** Кнопки групп клиентской НАВИГАЦИИ, управляющие панелями через aria-controls. */
const groupButtons = Array.from(
  document.querySelectorAll('button[data-collapse-group="client-nav"][aria-controls]')
);

/** Быстрый доступ к панелям групп по id из aria-controls. */
const groupPanelById = new Map(groupButtons.map((button) => [button.getAttribute("aria-controls"), null]));

groupPanelById.forEach((_, panelId) => {
  groupPanelById.set(panelId, document.getElementById(panelId));
});

/**
 * Синхронизирует визуальное состояние кнопки группы с состоянием панели.
 * - aria-expanded: для доступности.
 * - rotate-180 на стрелке: для визуальной индикации раскрытия.
 *
 * @param {HTMLButtonElement} button - Кнопка группы.
 * @param {boolean} isOpen - true, если панель раскрыта.
 */
function setGroupButtonState(button, isOpen) {
  button.setAttribute("aria-expanded", String(isOpen));

  const chevron = button.querySelector("[data-nav-chevron]");
  if (!chevron) return;

  chevron.classList.toggle("rotate-180", isOpen);
}

/**
 * Закрывает все группы, кроме выбранной кнопки.
 *
 * @param {HTMLButtonElement} currentButton - Кнопка группы, которую не нужно закрывать.
 */
function closeOtherPanels(currentButton) {
  groupButtons.forEach((button) => {
    if (button === currentButton) return;

    const panelId = button.getAttribute("aria-controls");
    const panel = groupPanelById.get(panelId);
    if (!panel) return;

    panel.classList.add("hidden");
    setGroupButtonState(button, false);
  });
}

/**
 * Инициализирует аккордеон:
 * - клик по закрытой группе открывает ее и закрывает остальные;
 * - клик по открытой группе закрывает ее.
 */
function initAccordion() {
  if (groupButtons.length === 0) return;

  // Синхронизируем начальное состояние стрелок, если часть панелей открыта на сервере.
  groupButtons.forEach((button) => {
    const panelId = button.getAttribute("aria-controls");
    const panel = groupPanelById.get(panelId);
    if (!panel) return;
    setGroupButtonState(button, !panel.classList.contains("hidden"));
  });

  groupButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const panelId = button.getAttribute("aria-controls");
      const panel = groupPanelById.get(panelId);
      if (!panel) return;

      const shouldOpen = panel.classList.contains("hidden");
      closeOtherPanels(button);

      if (shouldOpen) {
        panel.classList.remove("hidden");
        setGroupButtonState(button, true);
      } else {
        panel.classList.add("hidden");
        setGroupButtonState(button, false);
      }
    });
  });
}

initAccordion();
