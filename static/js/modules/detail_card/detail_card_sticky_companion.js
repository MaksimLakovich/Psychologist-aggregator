/**
 * Бизнес-смысл модуля:
 * Когда клиент прокручивает карточку вниз, ключевая информация о специалисте
 * (имя, рейтинг, цена) не должна теряться. Модуль делает "липкий компаньон"
 * в левой колонке, чтобы решение о записи принималось без лишнего скролла назад.
 */

// ===== STICKY COMPANION: перенос "Header + Price" под АВАТАР при скролле карточки клиента вниз =====
let headerObserver = null;
let stickyHeaderClone = null;

export function initStickyHeaderBehavior() {
    const header = document.getElementById("ps-main-header");
    const leftSlot = document.getElementById("ps-left-companion");

    if (!header || !leftSlot) return;

    // 1) ОТКЛЮЧАЕМ старый observer
    if (headerObserver) {
        headerObserver.disconnect();
        headerObserver = null;
    }

    // 2) УДАЛЯЕМ старый clone
    if (stickyHeaderClone) {
        stickyHeaderClone.remove();
        stickyHeaderClone = null;
    }

    // 3) Создаем clone ВСЕГДА заново
    stickyHeaderClone = header.cloneNode(true);
    stickyHeaderClone.id = "ps-main-header-clone";
    stickyHeaderClone.classList.add(
        "ps-header-clone",  // ДОБАВЛЯЮ кастомный стиль для clone под ФОТО ПСИХОЛОГА
        "opacity-0",
        "pointer-events-none",
        "transition-opacity",
        "duration-300"
    );

    leftSlot.appendChild(stickyHeaderClone);

    headerObserver = new IntersectionObserver(
        ([entry]) => {
            if (!entry.isIntersecting) {
                // показываем clone
                stickyHeaderClone.classList.remove("opacity-0", "pointer-events-none");
                stickyHeaderClone.classList.add("opacity-100");
                return;
            }
            // скрываем clone
            stickyHeaderClone.classList.add("opacity-0", "pointer-events-none");
            stickyHeaderClone.classList.remove("opacity-100");
        },
        {
            root: null,
            threshold: 0,
            rootMargin: "-80px 0px 0px 0px",
        }
    );

    headerObserver.observe(header);
}
