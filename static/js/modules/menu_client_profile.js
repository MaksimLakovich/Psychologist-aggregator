//-------------------------------------------------------------
// Когда нажимаем на меню, библиотека Flowbite добавляет или убирает класс hidden (скрытый) у выпадающего списка.
// Этот JS-код "следит" за этим процессом и как только список открывается, то он:
// - подсвечивает кнопку (меняет фон и цвет текста).
// - поворачивает иконку стрелочки на 180 градусов.
// - сообщает браузеру, что меню сейчас развернуто (важно для экранных дикторов).
//-------------------------------------------------------------

const menuButton = document.getElementById("user-menu-button");
const menuDropdown = document.getElementById("dropdown");

if (menuButton && menuDropdown) {
  const arrowIcon = menuButton.querySelector("svg");

  const syncMenuButtonState = () => {
    const isOpen = !menuDropdown.classList.contains("hidden");

    menuButton.setAttribute("aria-expanded", String(isOpen));
    menuButton.classList.toggle("text-indigo-700", isOpen);
    menuButton.classList.toggle("bg-gray-100", isOpen);

    if (arrowIcon) {
      arrowIcon.classList.toggle("rotate-180", isOpen);
    }
  };

  // Поддерживаем состояние кнопки в синхроне с dropdown, который открывает/закрывает Flowbite.
  const observer = new MutationObserver(syncMenuButtonState);
  observer.observe(menuDropdown, { attributes: true, attributeFilter: ["class"] });

  menuButton.addEventListener("click", () => {
    // Ждем, пока Flowbite переключит классы hidden/block.
    requestAnimationFrame(syncMenuButtonState);
  });

  document.addEventListener("click", (event) => {
    if (!menuButton.contains(event.target) && !menuDropdown.contains(event.target)) {
      requestAnimationFrame(syncMenuButtonState);
    }
  });

  syncMenuButtonState();
}
