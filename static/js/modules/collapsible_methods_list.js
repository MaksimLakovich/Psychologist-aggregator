/**
 * Общий модуль списка методов с возможностью сворачивания и разворачивания.
 *
 * Бизнес-задача этого файла:
 * - показать длинный список методов компактно там, где это нужно;
 * - дать странице возможность либо скрывать часть методов, либо показывать все сразу;
 * - переиспользоваться в разных сценариях без дублирования UI-логики.
 */

// Инициализирует список методов и подключает кнопку "Ещё / Скрыть", если она нужна.
// Для personal-questions используем свернутый режим с первыми 6 методами, а для каталога можно передать visibleCount=0 и сразу показать весь список.
export function initCollapsibleList({ containerSelector, buttonSelector, visibleCount = 6 }) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const showMoreBtn = buttonSelector ? document.querySelector(buttonSelector) : null;
    const items = container.querySelectorAll(".method-item");

    // Если visibleCount <= 0, значит на этой странице нужно сразу показать все методы и отключить механику сворачивания.
    if (!Number.isInteger(visibleCount) || visibleCount <= 0) {
        items.forEach((item) => item.classList.remove("hidden"));
        if (showMoreBtn) {
            showMoreBtn.classList.add("hidden");
        }
        return;
    }

    if (!showMoreBtn) return;

    const totalCount = items.length;
    const hiddenCount = Math.max(0, totalCount - visibleCount);
    let expanded = false;

    // Применяет текущее состояние списка: свернуто или развернуто.
    function applyState() {
        if (!expanded) {
            items.forEach((item, idx) => {
                if (idx >= visibleCount) {
                    item.classList.add("hidden");
                    return;
                }

                item.classList.remove("hidden");
            });

            if (hiddenCount > 0) {
                showMoreBtn.textContent = `Ещё ${hiddenCount}`;
                showMoreBtn.classList.remove("hidden");
            }
            return;
        }

        items.forEach((item) => item.classList.remove("hidden"));
        showMoreBtn.textContent = "Скрыть";
    }

    if (hiddenCount > 0) {
        showMoreBtn.classList.remove("hidden");
        applyState();
    }

    // Переключает список методов между свернутым и развернутым состоянием.
    showMoreBtn.addEventListener("click", () => {
        expanded = !expanded;
        applyState();
    });
}
