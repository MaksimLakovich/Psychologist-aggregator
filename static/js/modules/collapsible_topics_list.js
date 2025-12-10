export function initCollapsibleTopicGroups() {
    // Берем каждую группу тем
    const groups = document.querySelectorAll(".topics-group");

    groups.forEach(group => {
        const items = group.querySelectorAll(".topic-item");
        const showMoreBtn = group.parentElement.querySelector(".show-more-topics");

        if (!items.length || !showMoreBtn) return;

        const visibleCount = 6;
        const totalCount = items.length;
        const hiddenCount = Math.max(0, totalCount - visibleCount);

        if (hiddenCount <= 0) {
            showMoreBtn.classList.add("hidden");
            return;
        }

        let expanded = false;

        const apply = () => {
            if (!expanded) {
                items.forEach((item, idx) => {
                    if (idx < visibleCount) item.classList.remove("hidden");
                    else item.classList.add("hidden");
                });
                showMoreBtn.textContent = `Ещё ${hiddenCount}`;
            } else {
                items.forEach(item => item.classList.remove("hidden"));
                showMoreBtn.textContent = "Скрыть";
            }
        };

        // старт
        apply();
        showMoreBtn.classList.remove("hidden");

        showMoreBtn.addEventListener("click", () => {
            expanded = !expanded;
            apply();
        });
    });
}
