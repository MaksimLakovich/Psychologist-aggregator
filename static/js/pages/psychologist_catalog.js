/**
 * Страница каталога психологов.
 *
 * Отвечает за:
 * 1) Переключение вкладок внутри карточки: "Основное" / "О себе".
 * 2) Догрузку карточек по кнопке "Показать еще" (append вниз без перезагрузки страницы).
 */

function initCardTabs(scope = document) {
    const cards = scope.querySelectorAll("[data-catalog-card]");

    cards.forEach((card) => {
        const tabButtons = card.querySelectorAll("[data-tab-button]");
        const tabPanels = card.querySelectorAll("[data-tab-panel]");

        if (!tabButtons.length || !tabPanels.length) return;

        const activateTab = (target) => {
            tabButtons.forEach((button) => {
                const isActive = button.dataset.target === target;

                button.setAttribute("aria-selected", String(isActive));
                button.classList.toggle("bg-indigo-100", isActive);
                button.classList.toggle("text-indigo-700", isActive);
                button.classList.toggle("bg-gray-100", !isActive);
                button.classList.toggle("text-gray-600", !isActive);
            });

            tabPanels.forEach((panel) => {
                const isActive = panel.dataset.tabPanel === target;
                panel.classList.toggle("hidden", !isActive);
            });
        };

        // Важный guard: не навешиваем обработчики повторно при повторной инициализации.
        if (card.dataset.tabsInitialized === "1") return;

        tabButtons.forEach((button) => {
            button.addEventListener("click", () => {
                activateTab(button.dataset.target);
            });
        });

        // Явно фиксируем дефолтное состояние.
        activateTab("main");
        card.dataset.tabsInitialized = "1";
    });
}

function initLoadMore() {
    const grid = document.getElementById("catalog-cards-grid");
    const loadMoreButton = document.getElementById("catalog-load-more-btn");
    const errorLabel = document.getElementById("catalog-load-more-error");

    if (!grid || !loadMoreButton) return;

    loadMoreButton.addEventListener("click", async () => {
        const endpoint = loadMoreButton.dataset.endpoint;
        const nextPage = loadMoreButton.dataset.nextPage;
        const randomOrderKey = loadMoreButton.dataset.randomOrderKey;

        if (!endpoint || !nextPage || !randomOrderKey) {
            loadMoreButton.hidden = true;
            return;
        }

        loadMoreButton.disabled = true;
        if (errorLabel) errorLabel.classList.add("hidden");

        try {
            const params = new URLSearchParams({
                partial: "1",
                page: String(nextPage),
                order_key: String(randomOrderKey),
            });

            const response = await fetch(`${endpoint}?${params.toString()}`, {
                method: "GET",
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            if (data.status !== "ok") {
                throw new Error("invalid_response");
            }

            // Вставляем новые карточки в конец существующей сетки.
            const temp = document.createElement("div");
            temp.innerHTML = data.cards_html || "";

            const appendedCards = temp.querySelectorAll("[data-catalog-card]");
            appendedCards.forEach((card) => grid.appendChild(card));

            // Инициализируем табы только для новых карточек.
            initCardTabs(grid);

            if (data.has_next && data.next_page_number) {
                loadMoreButton.dataset.nextPage = String(data.next_page_number);
                loadMoreButton.dataset.randomOrderKey = String(data.random_order_key || randomOrderKey);
                loadMoreButton.hidden = false;
            } else {
                loadMoreButton.hidden = true;
            }
        } catch (error) {
            console.error("Ошибка догрузки карточек каталога:", error);
            if (errorLabel) errorLabel.classList.remove("hidden");
        } finally {
            loadMoreButton.disabled = false;
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initCardTabs();
    initLoadMore();
});
