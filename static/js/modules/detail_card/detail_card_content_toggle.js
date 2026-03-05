/**
 * Бизнес-смысл модуля:
 * На детальной карточке клиент читает длинные блоки (биография, образование)
 * и часто переключается между разными психологами. Этот модуль делает чтение
 * удобным: управляет сворачиванием/разворачиванием длинных блоков контента.
 */


// Регистрируем глобальные обработчики, потому что часть кнопок создается
// динамически через innerHTML и вызывает функции через inline onclick.
export function initGlobalTextToggleHandlers() {

    // 1) Функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (биография)
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

    // 2) Функция для кнопки СВЕРНУТЬ / РАЗВЕРНУТЬ (образование)
    window.toggleEducation = function (btn) {
        const list = btn.previousElementSibling;
        if (!list) return;

        const isCollapsed = list.dataset.collapsed === "true";
        list.dataset.collapsed = String(!isCollapsed);
        btn.textContent = isCollapsed ? "Показать меньше" : "Показать больше";
    };
}
