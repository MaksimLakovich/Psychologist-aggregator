/**
 * Подключает поведение "показать еще / скрыть" для сгруппированных списков тем.
 *
 * Почему этот модуль сделан с разными опциями (с "показать все" и без):
 * - на странице personal-questions нужно показывать только первые 6 тем в группе;
 * - на странице каталога psychologist_catalog нужно переиспользовать ту же DOM-логику,
 *   но показывать сразу все темы без обрезания.
 *
 * Обратно-совместимость:
 * - если функцию вызвать без аргументов, поведение останется как раньше: первые 6 тем.
 */
export function initCollapsibleTopicGroups({
    rootSelector = null,
    groupSelector = ".topics-group",
    itemSelector = ".topic-item",
    buttonSelector = ".show-more-topics",
    visibleCount = 6,
} = {}) {
    const rootElement = rootSelector ? document.querySelector(rootSelector) : document;
    if (!rootElement) return;

    const groups = rootElement.querySelectorAll(groupSelector);

    groups.forEach((group) => {
        const items = group.querySelectorAll(itemSelector);
        const showMoreBtn = group.parentElement?.querySelector(buttonSelector);

        if (!items.length || !showMoreBtn) return;

        // Если visibleCount не задан или равен 0/меньше,
        // считаем, что на этой странице нужно показать все темы сразу
        if (!Number.isInteger(visibleCount) || visibleCount <= 0) {
            items.forEach((item) => item.classList.remove("hidden"));
            showMoreBtn.classList.add("hidden");
            return;
        }

        const totalCount = items.length;
        const hiddenCount = Math.max(0, totalCount - visibleCount);

        if (hiddenCount <= 0) {
            showMoreBtn.classList.add("hidden");
            return;
        }

        let expanded = false;

        const applyState = () => {
            if (!expanded) {
                items.forEach((item, index) => {
                    if (index < visibleCount) item.classList.remove("hidden");
                    else item.classList.add("hidden");
                });
                showMoreBtn.textContent = `Ещё ${hiddenCount}`;
            } else {
                items.forEach((item) => item.classList.remove("hidden"));
                showMoreBtn.textContent = "Скрыть";
            }
        };

        // старт
        applyState();
        showMoreBtn.classList.remove("hidden");

        showMoreBtn.addEventListener("click", () => {
            expanded = !expanded;
            applyState();
        });
    });
}
