/**
 * Страница каталога психологов.
 *
 * Отвечает за:
 * 1) Переключение вкладок внутри карточки: "Основное" / "О себе".
 * 2) Догрузку карточек по кнопке "Показать еще" (append вниз без перезагрузки страницы).
 * 3) Сохранение состояния каталога перед переходом в детальную карточку:
 *    layout / random order / текущая страница / якорь выбранной карточки.
 */

const CATALOG_STATE_STORAGE_KEY = "psychologist_catalog_state_v1";
const CATALOG_STATE_TTL_MS = 1000 * 60 * 60 * 6; // 6 часов

function toPositiveInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed > 0) {
        return parsed;
    }
    return fallback;
}

function readCatalogState() {
    try {
        const rawState = window.sessionStorage.getItem(CATALOG_STATE_STORAGE_KEY);
        if (!rawState) return null;

        const parsedState = JSON.parse(rawState);
        if (!parsedState || typeof parsedState !== "object") return null;

        const updatedAt = toPositiveInt(parsedState.updated_at, null);
        if (updatedAt && Date.now() - updatedAt > CATALOG_STATE_TTL_MS) {
            window.sessionStorage.removeItem(CATALOG_STATE_STORAGE_KEY);
            return null;
        }

        return parsedState;
    } catch (error) {
        return null;
    }
}

function writeCatalogState(state) {
    try {
        window.sessionStorage.setItem(CATALOG_STATE_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
        // В некоторых браузерах/режимах хранилище может быть недоступно.
        // Это не должно ломать основной сценарий работы каталога.
    }
}

function collectCatalogState(loadMoreButton, extraState = {}) {
    if (!loadMoreButton) return null;

    const currentPage = toPositiveInt(loadMoreButton.dataset.currentPage, 1);
    const randomOrderKey = toPositiveInt(loadMoreButton.dataset.randomOrderKey, null);
    const layoutMode = loadMoreButton.dataset.layout === "sidebar" ? "sidebar" : "menu";

    return {
        layout_mode: layoutMode,
        current_page: currentPage,
        order_key: randomOrderKey,
        updated_at: Date.now(),
        ...extraState,
    };
}

function persistCatalogState(loadMoreButton, extraState = {}) {
    const baseState = collectCatalogState(loadMoreButton, extraState);
    if (!baseState) return;

    const previousState = readCatalogState() || {};
    writeCatalogState({
        ...previousState,
        ...baseState,
    });
}

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
        const layoutMode = loadMoreButton.dataset.layout;
        const requestedPage = toPositiveInt(nextPage, null);

        if (!endpoint || !requestedPage || !randomOrderKey) {
            loadMoreButton.hidden = true;
            return;
        }

        loadMoreButton.disabled = true;
        if (errorLabel) errorLabel.classList.add("hidden");

        try {
            const params = new URLSearchParams({
                partial: "1",
                page: String(requestedPage),
                order_key: String(randomOrderKey),
            });
            if (layoutMode) {
                params.append("layout", layoutMode);
            }

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

            // Зафиксировали, что до этой страницы пользователь уже догрузил каталог.
            loadMoreButton.dataset.currentPage = String(requestedPage);
            loadMoreButton.dataset.randomOrderKey = String(data.random_order_key || randomOrderKey);
            persistCatalogState(loadMoreButton);

            if (data.has_next && data.next_page_number) {
                loadMoreButton.dataset.nextPage = String(data.next_page_number);
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

function initCatalogStatePersistence() {
    const loadMoreButton = document.getElementById("catalog-load-more-btn");
    if (!loadMoreButton) return;

    // При первом рендере обновляем базовое состояние каталога.
    // Это нужно для сценария "перешел в detail без догрузки page=2".
    persistCatalogState(loadMoreButton, {
        anchor: null,
        scroll_y: Math.max(window.scrollY, 0),
    });

    document.addEventListener("click", (event) => {
        const detailLink = event.target.closest("[data-catalog-detail-link]");
        if (!detailLink) return;

        persistCatalogState(loadMoreButton, {
            anchor: detailLink.dataset.profileSlug || null,
            scroll_y: Math.max(window.scrollY, 0),
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initCardTabs();
    initCatalogStatePersistence();
    initLoadMore();
});
