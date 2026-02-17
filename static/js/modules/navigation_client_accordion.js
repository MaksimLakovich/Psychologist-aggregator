const groupButtons = Array.from(
  document.querySelectorAll('button[data-collapse-group="client-nav"][data-collapse-toggle]')
);
const navItems = Array.from(document.querySelectorAll("a[data-nav-item][data-nav-key]"));
const navGroupButtons = Array.from(document.querySelectorAll("button[data-nav-group-button][data-nav-group]"));
const groupButtonByName = new Map(navGroupButtons.map((button) => [button.dataset.navGroup, button]));
const groupPanelByTarget = new Map(
  groupButtons.map((button) => [button.getAttribute("data-collapse-toggle"), null])
);
const ACTIVE_ITEM_CLASSES = ["bg-slate-100/80", "text-slate-900", "font-medium"];
const INACTIVE_ITEM_CLASSES = ["font-normal"];
const ACTIVE_GROUP_CLASSES = ["font-extrabold"];
const INACTIVE_GROUP_CLASSES = ["font-normal"];
const STORAGE_KEY = "client_sidebar_active_nav_item";

groupPanelByTarget.forEach((_, targetId) => {
  groupPanelByTarget.set(targetId, document.getElementById(targetId));
});

function getStoredNavKey() {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch (error) {
    return null;
  }
}

function setStoredNavKey(value) {
  try {
    sessionStorage.setItem(STORAGE_KEY, value);
  } catch (error) {
    // Ignore storage errors (private mode / blocked storage).
  }
}

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

function syncNavItemStateFromStorage() {
  if (navItems.length === 0) return;
  const storedKey = getStoredNavKey();
  if (!storedKey) return;
  const savedItem = navItems.find((item) => item.dataset.navKey === storedKey);
  if (!savedItem) return;
  setActiveNavItem(savedItem);
}

if (groupButtons.length > 0) {
  groupButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.getAttribute("data-collapse-toggle");
      const targetPanel = groupPanelByTarget.get(targetId);
      if (!targetPanel) return;

      const targetWillOpen = targetPanel.classList.contains("hidden");
      if (!targetWillOpen) return;

      groupButtons.forEach((otherButton) => {
        if (otherButton === button) return;

        const otherId = otherButton.getAttribute("data-collapse-toggle");
        const otherPanel = groupPanelByTarget.get(otherId);
        if (!otherPanel) return;

        otherPanel.classList.add("hidden");
      });
    });
  });
}

if (navItems.length > 0) {
  syncNavItemStateFromStorage();

  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      setActiveNavItem(item);
      setStoredNavKey(item.dataset.navKey);
    });
  });
}
