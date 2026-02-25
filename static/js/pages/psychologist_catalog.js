/**
 * Страница каталога психологов (краткие карточки).
 *
 * Что делает этот файл:
 * 1) Управляет вкладками внутри карточки: "Основное" / "О себе".
 * 2) Реализует кнопку "Показать еще" (AJAX-догрузка следующей страницы без перезагрузки).
 * 3) Сохраняет техническое состояние каталога в sessionStorage, чтобы при возврате
 *    из детальной карточки можно было восстановить тот же порядок/страницу/позицию.
 *
 * Важно:
 * - Это клиентская зона (авторизованный пользователь), поэтому хранение такого технического
 *   состояния в sessionStorage безопасно и уместно.
 * - Любые ошибки работы sessionStorage не должны ломать основной UX каталога.
 */

const CATALOG_STATE_STORAGE_KEY = "psychologist_catalog_state_v1";
const CATALOG_STATE_TTL_MS = 1000 * 60 * 60 * 6; // 6 часов

/**
 * Преобразует значение в целое число > 0.
 * Используем для page, timestamps и других параметров, где 0 невалиден.
 */
function toPositiveInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed > 0) {
        return parsed;
    }
    return fallback;
}

/**
 * Преобразует значение в целое число >= 0.
 * Используем для order_key: значение 0 допустимо.
 */
function toNonNegativeInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed >= 0) {
        return parsed;
    }
    return fallback;
}

/**
 * Читает текущее сохраненное состояние каталога из sessionStorage.
 *
 * Возвращает:
 * - объект состояния, если оно валидно и не просрочено;
 * - null, если состояния нет/оно битое/истекло.
 */
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

/**
 * Записывает состояние каталога в sessionStorage.
 * Любые ошибки хранилища молча игнорируем, чтобы не ломать рабочий поток пользователя.
 */
function writeCatalogState(state) {
    try {
        window.sessionStorage.setItem(CATALOG_STATE_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
        // В некоторых браузерах/режимах хранилище может быть недоступно.
        // Это не должно ломать основной сценарий работы каталога
    }
}

/**
 * Собирает базовое состояние каталога из текущего DOM кнопки "Показать еще".
 *
 * Источник данных:
 * - data-атрибуты кнопки (layout, currentPage, randomOrderKey).
 * - дополнительные данные extraState (например, anchor выбранной карточки).
 */
function collectCatalogState(loadMoreButton, extraState = {}) {
    if (!loadMoreButton) return null;

    const currentPage = toPositiveInt(loadMoreButton.dataset.currentPage, 1);
    const randomOrderKey = toNonNegativeInt(loadMoreButton.dataset.randomOrderKey, null);
    const layoutMode = loadMoreButton.dataset.layout === "sidebar" ? "sidebar" : "menu";

    return {
        layout_mode: layoutMode,
        current_page: currentPage,
        order_key: randomOrderKey,
        updated_at: Date.now(),
        ...extraState,
    };
}

/**
 * Сохраняет состояние каталога:
 * 1) читает предыдущее состояние;
 * 2) поверх него накладывает актуальные значения;
 * 3) пишет объединенный объект обратно в storage.
 */
function persistCatalogState(loadMoreButton, extraState = {}) {
    const baseState = collectCatalogState(loadMoreButton, extraState);
    if (!baseState) return;

    const previousState = readCatalogState() || {};
    writeCatalogState({
        ...previousState,
        ...baseState,
    });
}

/**
 * Инициализирует вкладки карточек.
 *
 * Логика:
 * - у каждой карточки две вкладки: "main" и "bio";
 * - при переключении меняем стили кнопок и видимость панелей;
 * - защищаемся от повторной инициализации одной и той же карточки.
 */
function initCardTabs(scope = document) {
    const cards = scope.querySelectorAll("[data-catalog-card]");

    cards.forEach((card) => {
        const tabButtons = card.querySelectorAll("[data-tab-button]");
        const tabPanels = card.querySelectorAll("[data-tab-panel]");

        if (!tabButtons.length || !tabPanels.length) return;
        if (card.dataset.tabsInitialized === "1") return;

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

        tabButtons.forEach((button) => {
            button.addEventListener("click", () => {
                activateTab(button.dataset.target);
            });
        });

        // По умолчанию открываем "Основное"
        activateTab("main");
        card.dataset.tabsInitialized = "1";
    });
}

/**
 * Инициализирует кнопку "Показать еще".
 *
 * Шаги на клик:
 * 1) валидируем входные параметры;
 * 2) отправляем GET partial-запрос за следующей страницей;
 * 3) добавляем карточки в текущую сетку;
 * 4) переинициализируем вкладки для новых карточек;
 * 5) обновляем data-атрибуты кнопки и состояние storage.
 */
function initLoadMore() {
    const grid = document.getElementById("catalog-cards-grid");
    const loadMoreButton = document.getElementById("catalog-load-more-btn");
    const errorLabel = document.getElementById("catalog-load-more-error");

    if (!grid || !loadMoreButton) return;

    loadMoreButton.addEventListener("click", async () => {
        const endpoint = loadMoreButton.dataset.endpoint;
        const requestedPage = toPositiveInt(loadMoreButton.dataset.nextPage, null);
        const orderKey = toNonNegativeInt(loadMoreButton.dataset.randomOrderKey, null);
        const layoutMode = loadMoreButton.dataset.layout;

        if (!endpoint || !requestedPage || orderKey === null) {
            loadMoreButton.hidden = true;
            return;
        }

        loadMoreButton.disabled = true;
        if (errorLabel) errorLabel.classList.add("hidden");

        try {
            const params = new URLSearchParams({
                partial: "1",
                page: String(requestedPage),
                order_key: String(orderKey),
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

            // Вставляем новые карточки в конец текущего списка
            const temp = document.createElement("div");
            temp.innerHTML = data.cards_html || "";
            const appendedCards = temp.querySelectorAll("[data-catalog-card]");
            appendedCards.forEach((card) => grid.appendChild(card));

            // Инициализация вкладок только для карточек, которые еще не инициализированы
            initCardTabs(grid);

            // Фиксируем, что пользователь уже догрузил эту страницу
            loadMoreButton.dataset.currentPage = String(requestedPage);

            // Сервер возвращает random_order_key; он может быть 0, это валидно
            const refreshedOrderKey = toNonNegativeInt(data.random_order_key, orderKey);
            loadMoreButton.dataset.randomOrderKey = String(refreshedOrderKey);

            // Сохраняем обновленное состояние каталога для корректного возврата из detail
            persistCatalogState(loadMoreButton);

            const nextPageNumber = toPositiveInt(data.next_page_number, null);
            if (data.has_next && nextPageNumber) {
                loadMoreButton.dataset.nextPage = String(nextPageNumber);
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

/**
 * Включает сохранение состояния каталога перед переходом в detail.
 *
 * Что сохраняем:
 * - базовое состояние (layout/page/order_key) при загрузке страницы;
 * - anchor выбранной карточки и текущий scroll перед переходом в detail.
 */
function initCatalogStatePersistence() {
    const loadMoreButton = document.getElementById("catalog-load-more-btn");
    if (!loadMoreButton) return;

    // Обновляем базовое состояние сразу при рендере каталога.
    // Нужен сценарий: пользователь открывает detail с page=1 без нажатия "Показать еще"
    persistCatalogState(loadMoreButton, {
        anchor: null,
        scroll_y: Math.max(window.scrollY, 0),
    });

    // Делегируем обработчик на document, чтобы он работал и для карточек, догруженных AJAX
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
