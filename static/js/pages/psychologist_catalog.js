import {
    readCatalogState,
    toNonNegativeInt,
    toPositiveInt,
    writeCatalogState,
} from "../modules/catalog_state.js";

/**
 * Логика страницы "Каталог психологов".
 *
 * Этот файл отвечает за 3 задачи:
 * 1) Переключение вкладок внутри карточки ("Основное" / "О себе").
 * 2) Кнопку "Показать еще" (догрузка новых карточек без перезагрузки страницы).
 * 3) Сохранение состояния каталога перед переходом в детальный профиль.
 *
 * Пример пользовательского сценария:
 * - клиент открыл каталог, нажал "Показать еще" до page=3;
 * - открыл карточку психолога;
 * - нажал "Назад в каталог";
 * - система должна помнить page=3 и порядок карточек.
 *
 * Важное уточнение по архитектуре:
 * - основной "идеальный" возврат обычно делает браузерный history.back();
 * - сохранение состояния в sessionStorage (через общий модуль) - это дополнительная
 *   защитная ветка для fallback-сценариев.
 * То есть это хорошая практика "на будущее" с почти нулевой стоимостью.
 */

/**
 * Собирает "базовое состояние" каталога из data-атрибутов кнопки "Показать еще".
 *
 * Что собираем:
 * - layout_mode (menu/sidebar);
 * - current_page (до какой страницы уже догрузили);
 * - order_key (чтобы не пересортировать карточки при возврате);
 * - updated_at (время обновления состояния).
 *
 * extraState нужен для добавления контекста конкретного действия.
 * Пример: при клике по карточке передаем anchor выбранного психолога.
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
 * Сохраняет состояние каталога в sessionStorage.
 *
 * Почему merge с предыдущим состоянием:
 * - иногда обновляем не все поля сразу;
 * - хотим не потерять уже сохраненные значения.
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
 * Обновляет текстовый индикатор текущей страницы внизу каталога.
 *
 * Пример:
 * - если currentPage = 1 и totalPages = 12, показываем "1 из 12";
 * - после догрузки page=2 показываем "2 из 12".
 */
function renderCurrentPageIndicator(currentPage, totalPages) {
    const indicator = document.getElementById("catalog-page-indicator");
    if (!indicator) return;

    const safeTotalPages = toNonNegativeInt(totalPages, 0);
    if (safeTotalPages === 0) {
        indicator.textContent = "0 из 0";
        return;
    }

    const safeCurrentPage = toPositiveInt(currentPage, 1);
    const normalizedCurrentPage = Math.min(safeCurrentPage, safeTotalPages);
    indicator.textContent = `${normalizedCurrentPage} из ${safeTotalPages}`;
}

/**
 * Инициализирует вкладки внутри карточек.
 *
 * Как это работает:
 * - у каждой карточки есть 2 кнопки-вкладки и 2 панели контента;
 * - при клике выделяем активную кнопку;
 * - показываем нужную панель и скрываем вторую.
 *
 * Важный момент:
 * - карточки могут догружаться AJAX-ом;
 * - поэтому у каждой карточки ставим флаг tabsInitialized, чтобы не
 *   навешивать обработчики повторно.
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

        // Дефолтный режим карточки: вкладка "Основное".
        activateTab("main");
        card.dataset.tabsInitialized = "1";
    });
}

/**
 * Инициализирует кнопку "Показать еще".
 *
 * Алгоритм при клике:
 * 1) берем page/order_key/layout из data-атрибутов;
 * 2) запрашиваем partial-HTML следующей страницы;
 * 3) добавляем новые карточки вниз;
 * 4) обновляем состояние кнопки (currentPage, nextPage, orderKey);
 * 5) сохраняем актуальное состояние в sessionStorage.
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
        const totalPages = toNonNegativeInt(loadMoreButton.dataset.totalPages, 0);
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

            // Временный контейнер нужен, чтобы безопасно распарсить пришедший HTML.
            const temp = document.createElement("div");
            temp.innerHTML = data.cards_html || "";
            const appendedCards = temp.querySelectorAll("[data-catalog-card]");
            appendedCards.forEach((card) => grid.appendChild(card));

            // После добавления новых карточек запускаем инициализацию вкладок.
            initCardTabs(grid);

            // Фиксируем прогресс пагинации (до какой страницы пользователь дошел).
            loadMoreButton.dataset.currentPage = String(requestedPage);
            renderCurrentPageIndicator(requestedPage, totalPages);

            // Берем новый order_key от сервера (если есть), иначе оставляем текущий.
            const refreshedOrderKey = toNonNegativeInt(data.random_order_key, orderKey);
            loadMoreButton.dataset.randomOrderKey = String(refreshedOrderKey);

            // Сохраняем обновленное состояние для корректного возврата из detail.
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
 * Инициализирует кнопку "Вернуться в начало".
 *
 * При клике выполняется плавный скролл к началу страницы.
 * Это удобно после просмотра page=2/page=3, когда пользователь хочет быстро
 * вернуться к заголовку и первым карточкам.
 */
function initScrollToTopButton() {
    const scrollTopButton = document.getElementById("catalog-scroll-top-btn");
    if (!scrollTopButton) return;

    scrollTopButton.addEventListener("click", () => {
        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    });
}

/**
 * Включает сохранение состояния каталога.
 *
 * Что делаем:
 * - при загрузке страницы сохраняем базовое состояние;
 * - при клике на "Смотреть полный профиль" сохраняем anchor выбранной карточки.
 *
 * Зачем anchor:
 * - когда пользователь вернется назад, можно прокрутить к нужной карточке.
 *
 * Почему сохраняем это заранее, даже если обычно срабатывает history.back():
 * - если detail откроют нестандартно (например, прямая ссылка, новая вкладка, внешний переход),
 *   то fallback-логика все равно сможет восстановить каталог максимально близко к прежнему виду.
 */
function initCatalogStatePersistence() {
    const loadMoreButton = document.getElementById("catalog-load-more-btn");
    if (!loadMoreButton) return;

    // Первичное состояние нужно даже если пользователь не нажимал "Показать еще".
    persistCatalogState(loadMoreButton, {
        anchor: null,
        scroll_y: Math.max(window.scrollY, 0),
    });

    // Делегирование на document: работает и для карточек, пришедших через AJAX.
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
    const loadMoreButton = document.getElementById("catalog-load-more-btn");
    const initialPage = loadMoreButton ? toPositiveInt(loadMoreButton.dataset.currentPage, 1) : 1;
    const totalPages = loadMoreButton ? toNonNegativeInt(loadMoreButton.dataset.totalPages, 0) : 0;
    renderCurrentPageIndicator(initialPage, totalPages);

    initCardTabs();
    initCatalogStatePersistence();
    initLoadMore();
    initScrollToTopButton();
});
