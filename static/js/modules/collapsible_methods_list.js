export function initCollapsibleList({ containerSelector, buttonSelector, visibleCount = 6 }) {
    const container = document.querySelector(containerSelector);
    const showMoreBtn = document.querySelector(buttonSelector);

    if (!container || !showMoreBtn) return;

    const items = container.querySelectorAll(".method-item");
    const totalCount = items.length; // Считаем, сколько всего
    const hiddenCount = Math.max(0, totalCount - visibleCount); // Считаем, сколько скрыто

    let expanded = false; // состояние: false = свернуто, true = развернуто

    // Инициализация: скрываем лишние элементы
    function applyState() {
        // свернуто
        if (!expanded) {
            items.forEach((item, idx) => {
                if (idx >= visibleCount) item.classList.add("hidden");
                else item.classList.remove("hidden");
            });
            if (hiddenCount > 0) {
                showMoreBtn.textContent = `Ещё ${hiddenCount}`;
                showMoreBtn.classList.remove("hidden");
            }
        } else {
        // развернуто
            items.forEach(item => item.classList.remove("hidden"));
            showMoreBtn.textContent = "Скрыть";
        }
    }

    // Первичная настройка
    if (hiddenCount > 0) {
        showMoreBtn.classList.remove("hidden");
        applyState();
    }

    // Обработчик кнопки
    showMoreBtn.addEventListener("click", () => {
        expanded = !expanded; // переключаем состояние
        applyState();
    });
}
