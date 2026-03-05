/**
 * Бизнес-смысл модуля:
 * На детальной карточке клиент читает длинные блоки (биография, образование)
 * и часто переключается между разными психологами. Этот модуль делает чтение
 * удобным: управляет сворачиванием/разворачиванием текста и аккуратной
 * прокруткой к началу карточки перед ее перерисовкой.
 */


// 1) Функция для хранения состояния страницы выбора (при обновлении браузер)
// Проверяем, была ли страница перезагружена (для восстановления выбранного психолога)
export function isPageReload() {
    const nav = performance.getEntriesByType("navigation")[0];
    return Boolean(nav && nav.type === "reload");
}

// Регистрируем глобальные обработчики, потому что часть кнопок создается
// динамически через innerHTML и вызывает функции через inline onclick.
export function initGlobalTextToggleHandlers() {

    // 2) Функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (биография)
    window.toggleBiography = function (btn) {
        const wrapper = btn.previousElementSibling;
        if (!wrapper) return;

        const text = wrapper.querySelector(".biography-text");
        const fade = wrapper.querySelector(".biography-fade");
        if (!text) return;

        const isCollapsed = text.dataset.collapsed === "true";
        text.dataset.collapsed = String(!isCollapsed);
        btn.textContent = isCollapsed ? "Показать меньше" : "Показать больше";

        if (fade) {
            fade.style.display = isCollapsed ? "none" : "block";
        }
    };

    // 3) Функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (образование)
    window.toggleEducation = function (btn) {
        const list = btn.previousElementSibling;
        if (!list) return;

        const isCollapsed = list.dataset.collapsed === "true";
        list.dataset.collapsed = String(!isCollapsed);
        btn.textContent = isCollapsed ? "Показать меньше" : "Показать больше";
    };
}

// 4) Функция для автоматической плавной прокрутки к началу страницы при переключении между карточками специалистов
// Плавно скроллим наверх и ждем завершения скролла, затем выполняем callback
export function scrollToTopThen(callback) {
    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });

    // ждем пока автоматический scroll вверх реально завершится
    let lastY = window.scrollY;
    let sameCount = 0;

    const check = () => {
        const currentY = window.scrollY;

        if (currentY === lastY) {
            sameCount += 1;
        } else {
            sameCount = 0;
            lastY = currentY;
        }

        // scroll стабилизировался
        if (sameCount >= 3) {
            if (typeof callback === "function") {
                callback();
            }
            return;
        }

        requestAnimationFrame(check);
    };

    requestAnimationFrame(check);
}
