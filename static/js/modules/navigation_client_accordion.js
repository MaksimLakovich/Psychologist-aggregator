/**
 * Модуль управления клиентской боковой навигацией.
 *
 * Что делает:
 * 1) Управляет аккордеоном групп (в один момент открыта только одна группа).
 * 2) Подсвечивает выбранный пункт меню.
 * 3) Делает заголовок родительской группы "жирным", если выбран пункт внутри этой группы.
 * 4) Хранит выбранный пункт в sessionStorage для сохранения состояния при перезагрузке вкладки.
 *
 * Важно:
 * - Логика аккордеона реализована вручную (без автотоггла сторонних библиотек),
 *   чтобы исключить двойные переключения и баг "нужен второй клик для открытия".
 */

/** Кнопки групп аккордеона в клиентском сайдбаре */
const groupButtons = Array.from(
  document.querySelectorAll('button[data-collapse-group="client-nav"][aria-controls]')
);

/** Кликабельные пункты меню, которые должны подсвечиваться как выбранные */
const navItems = Array.from(document.querySelectorAll("a[data-nav-item][data-nav-key]"));

/** Кнопки-заголовки групп, которые выделяем при выборе вложенного пункта */
const navGroupButtons = Array.from(document.querySelectorAll("button[data-nav-group-button][data-nav-group]"));

/** Быстрый доступ к кнопке группы по ее имени (без повторного find на каждом клике) */
const groupButtonByName = new Map(navGroupButtons.map((button) => [button.dataset.navGroup, button]));

/** Быстрый доступ к панели группы по id из aria-controls */
const groupPanelByTarget = new Map(groupButtons.map((button) => [button.getAttribute("aria-controls"), null]));

/** Наборы классов для визуального состояния пунктов и групп */
const ACTIVE_ITEM_CLASSES = ["bg-slate-100/80", "text-slate-900", "font-medium"];
const INACTIVE_ITEM_CLASSES = ["font-normal"];
const ACTIVE_GROUP_CLASSES = ["font-extrabold"];
const INACTIVE_GROUP_CLASSES = ["font-normal"];

/** Ключ для хранения выбранного пункта меню в пределах текущей вкладки браузера */
const STORAGE_KEY = "client_sidebar_active_nav_item";

groupPanelByTarget.forEach((_, targetId) => {
  groupPanelByTarget.set(targetId, document.getElementById(targetId));
});

/**
 * Безопасно читает ключ активного пункта из sessionStorage.
 * Возвращает null, если storage недоступен (например, в приватном режиме)
 */
function getStoredNavKey() {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch (error) {
    return null;
  }
}

/**
 * Безопасно сохраняет ключ активного пункта в sessionStorage.
 * Если storage недоступен, просто игнорирует ошибку без падения UI
 */
function setStoredNavKey(value) {
  try {
    sessionStorage.setItem(STORAGE_KEY, value);
  } catch (error) {
    // Нам не критично, если состояние не сохранится между перезагрузками вкладки
  }
}

/**
 * Устанавливает визуально активный пункт меню.
 * Одновременно:
 * - снимает подсветку со всех остальных пунктов;
 * - сбрасывает выделение групп;
 * - выделяет родительскую группу (font-extrabold), если пункт вложенный
 */
function setActiveNavItem(activeItem) {
  navItems.forEach((item) => {
    if (item === activeItem) {
      item.classList.add(...ACTIVE_ITEM_CLASSES);
      item.classList.remove(...INACTIVE_ITEM_CLASSES);
      return;
    }
    item.classList.remove(...ACTIVE_ITEM_CLASSES);
    item.classList.add(...INACTIVE_ITEM_CLASSES);
  });

  navGroupButtons.forEach((button) => {
    button.classList.remove(...ACTIVE_GROUP_CLASSES);
    button.classList.add(...INACTIVE_GROUP_CLASSES);
  });

  if (!activeItem) return;

  const parentGroup = activeItem.dataset.navParentGroup;
  if (!parentGroup) return;

  const groupButton = groupButtonByName.get(parentGroup);
  if (!groupButton) return;

  groupButton.classList.remove(...INACTIVE_GROUP_CLASSES);
  groupButton.classList.add(...ACTIVE_GROUP_CLASSES);
}

/**
 * Восстанавливает подсветку пункта из sessionStorage.
 * Если сохраненного ключа нет или пункт в DOM отсутствует, ничего не делает
 */
function syncNavItemStateFromStorage() {
  if (navItems.length === 0) return;
  const storedKey = getStoredNavKey();
  if (!storedKey) return;

  const savedItem = navItems.find((item) => item.dataset.navKey === storedKey);
  if (!savedItem) return;

  setActiveNavItem(savedItem);
}

/**
 * Находит пункт, который сервер пометил активным для текущего маршрута.
 * Такой пункт имеет приоритет над состоянием из sessionStorage.
 */
function getServerActiveNavItem() {
  return document.querySelector("a[data-nav-item][data-nav-active-server='1']");
}

/**
 * Закрывает все панели групп, кроме указанной
 */
function closeOtherPanels(currentButton) {
  groupButtons.forEach((button) => {
    if (button === currentButton) return;
    const panelId = button.getAttribute("aria-controls");
    const panel = groupPanelByTarget.get(panelId);
    if (!panel) return;
    panel.classList.add("hidden");
  });
}

/**
 * Инициализирует поведение аккордеона:
 * - 1-й клик по закрытой группе открывает ее и закрывает остальные;
 * - клик по открытой группе закрывает ее;
 * - не требуется второй клик для открытия следующей группы
 */
function initAccordion() {
  if (groupButtons.length === 0) return;

  groupButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const panelId = button.getAttribute("aria-controls");
      const panel = groupPanelByTarget.get(panelId);
      if (!panel) return;

      const shouldOpen = panel.classList.contains("hidden");
      closeOtherPanels(button);

      if (shouldOpen) {
        panel.classList.remove("hidden");
      } else {
        panel.classList.add("hidden");
      }
    });
  });
}

/**
 * Инициализирует подсветку выбранного пункта меню:
 * - восстанавливает прошлый выбор;
 * - обновляет подсветку и storage при клике на пункт
 */
function initNavItemHighlighting() {
  if (navItems.length === 0) return;

  const serverActiveItem = getServerActiveNavItem();
  if (serverActiveItem) {
    setActiveNavItem(serverActiveItem);
    setStoredNavKey(serverActiveItem.dataset.navKey);
  } else {
    syncNavItemStateFromStorage();
  }

  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      setActiveNavItem(item);
      setStoredNavKey(item.dataset.navKey);
    });
  });
}

initAccordion();
initNavItemHighlighting();
