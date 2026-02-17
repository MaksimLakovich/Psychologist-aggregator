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
const OPEN_PANEL_CLASSES = ["max-h-80", "opacity-100", "translate-y-0", "pointer-events-auto", "py-2"];
const CLOSED_PANEL_CLASSES = ["max-h-0", "opacity-0", "-translate-y-1", "pointer-events-none"];

groupPanelById.forEach((_, panelId) => {
  groupPanelById.set(panelId, document.getElementById(panelId));
});

/**
 * Проверяет, открыта ли панель по текущему набору классов.
 *
 * @param {HTMLElement} panel - Панель группы.
 * @returns {boolean} true, если панель в состоянии "открыто".
 */
function isPanelOpen(panel) {
  return panel.classList.contains("max-h-80");
}

/**
 * Переключает панель в состояние открыто/закрыто с плавной анимацией.
 *
 * @param {HTMLElement} panel - Панель группы.
 * @param {boolean} isOpen - true для открытия, false для закрытия.
 */
function setPanelState(panel, isOpen) {
  panel.classList.remove(...OPEN_PANEL_CLASSES, ...CLOSED_PANEL_CLASSES);
  panel.classList.add(...(isOpen ? OPEN_PANEL_CLASSES : CLOSED_PANEL_CLASSES));
}

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

    setPanelState(panel, false);
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
    const opened = isPanelOpen(panel);
    setPanelState(panel, opened);
    setGroupButtonState(button, opened);
  });

  groupButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const panelId = button.getAttribute("aria-controls");
      const panel = groupPanelById.get(panelId);
      if (!panel) return;

      const shouldOpen = !isPanelOpen(panel);
      closeOtherPanels(button);

      setPanelState(panel, shouldOpen);
      setGroupButtonState(button, shouldOpen);
    });
  });
}

initAccordion();
