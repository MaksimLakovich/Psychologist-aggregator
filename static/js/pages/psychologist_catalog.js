import {
    readCatalogState,
    toNonNegativeInt,
    toPositiveInt,
    writeCatalogState,
} from "../modules/catalog_state.js";
import { initMultiToggle } from "../modules/toggle_group_multi_choice.js";
import { pluralizeRu } from "../utils/pluralize_ru.js";

// Список технических query-параметров фильтров каталога, которые не должны
// оставаться в пользовательском URL в адресной строке.
// Сейчас тут только первый реализованный фильтр, но при добавлении новых
// фильтров каталога этот список можно будет расширять.
const CATALOG_FILTER_QUERY_KEYS = [
    "consultation_type",
];

/**
 * Логика страницы "Каталог психологов".
 *
 * Этот файл отвечает за 4 задачи:
 * 1) Переключение вкладок внутри карточки ("Основное" / "О себе").
 * 2) Кнопку "Показать еще" (догрузка новых карточек без перезагрузки страницы).
 * 3) Сохранение состояния каталога перед переходом в детальный профиль.
 * 4) Работу модалки фильтров каталога (на текущем шаге: "Вид консультации").
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
 * Текст на кнопке применения фильтра.
 */
const APPLY_RESULTS_LABEL = "Показать результаты";

/**
 * Кешируем прочитанные из DOM данные, чтобы не парсить script-теги повторно.
 */
let cachedConsultationTypeChoices = null;
let cachedConsultationTypeCounts = null;
let cachedActiveConsultationType = null;
let isActiveConsultationTypeLoaded = false;

/**
 * Безопасно читает JSON из script-тега.
 *
 * Если тега нет или JSON битый, возвращаем fallback.
 */
function readJsonScript(id, fallback) {
    const scriptTag = document.getElementById(id);
    if (!scriptTag) return fallback;

    try {
        return JSON.parse(scriptTag.textContent || "null") ?? fallback;
    } catch (error) {
        return fallback;
    }
}

/**
 * Возвращает mapping вариантов вида консультации.
 *
 * Источник истины:
 * - backend передает сюда CLIENT_TO_TOPIC_TYPE_MAP,
 *   то есть мы не дублируем словарь на frontend.
 */
function getConsultationTypeChoices() {
    if (cachedConsultationTypeChoices !== null) {
        return cachedConsultationTypeChoices;
    }

    const rawChoices = readJsonScript("catalog-consultation-type-choices-data", {});
    cachedConsultationTypeChoices = rawChoices && typeof rawChoices === "object" ? rawChoices : {};
    return cachedConsultationTypeChoices;
}

/**
 * Возвращает предрассчитанные количества карточек по варианту вида консультации.
 *
 * Формат:
 * {
 *   all: 40,
 *   individual: 39,
 *   couple: 4,
 * }
 */
function getConsultationTypeCounts() {
    if (cachedConsultationTypeCounts !== null) {
        return cachedConsultationTypeCounts;
    }

    const rawCounts = readJsonScript("catalog-consultation-type-counts-data", {});
    const parseCount = (value) => {
        const parsed = Number.parseInt(String(value), 10);
        return Number.isInteger(parsed) && parsed >= 0 ? parsed : 0;
    };

    cachedConsultationTypeCounts = {
        all: parseCount(rawCounts.all),
        individual: parseCount(rawCounts.individual),
        couple: parseCount(rawCounts.couple),
    };
    return cachedConsultationTypeCounts;
}

/**
 * Возвращает активное значение фильтра из backend-контекста.
 *
 * Возвращает:
 * - "individual" или "couple" если фильтр активен;
 * - null если фильтр не выбран и каталог открыт в режиме "все".
 */
function getActiveConsultationTypeFromDOM() {
    if (isActiveConsultationTypeLoaded) {
        return cachedActiveConsultationType;
    }

    const rawValue = readJsonScript("catalog-active-consultation-type-data", null);
    cachedActiveConsultationType = normalizeConsultationType(rawValue);
    isActiveConsultationTypeLoaded = true;
    return cachedActiveConsultationType;
}

/**
 * Нормализует входное значение вида консультации.
 *
 * Если значение отсутствует или не входит в допустимые ключи,
 * возвращаем null, что означает "фильтр не выбран".
 */
function normalizeConsultationType(rawValue) {
    if (typeof rawValue !== "string") return null;

    const choices = getConsultationTypeChoices();
    if (Object.prototype.hasOwnProperty.call(choices, rawValue)) {
        return rawValue;
    }

    return null;
}

/**
 * Возвращает выбранное значение в модалке.
 *
 * Если активных кнопок нет, возвращаем null.
 */
function getModalSelectedConsultationType() {
    const hiddenInput = document.querySelector("#catalog-consultation-hidden-inputs input");
    return normalizeConsultationType(hiddenInput ? hiddenInput.value : null);
}

/**
 * Перерисовывает кнопку "Показать результаты" с количеством найденных психологов.
 *
 * Пример:
 * Показать результаты
 * Найдено: 4 специалиста
 */
function renderApplyButtonWithCount(applyButton, selectedConsultationType) {
    if (!applyButton) return;

    const counts = getConsultationTypeCounts();
    const countKey = selectedConsultationType || "all";
    const selectedCount = counts[countKey] ?? counts.all ?? 0;
    const specialistWord = pluralizeRu(
        selectedCount,
        "специалист",
        "специалиста",
        "специалистов",
    );

    applyButton.innerHTML = `
        ${APPLY_RESULTS_LABEL}
        <span class="block mt-1 text-xs font-medium text-indigo-100">
            Найдено: ${selectedCount} ${specialistWord}
        </span>
    `;
}

/**
 * Возвращает базовый endpoint каталога.
 */
function resolveCatalogEndpoint() {
    const loadMoreButton = document.getElementById("catalog-load-more-btn");
    return loadMoreButton?.dataset.endpoint || window.location.pathname;
}

/**
 * Возвращает активный режим layout.
 *
 * Приоритет:
 * 1) data-layout у кнопки "Показать еще";
 * 2) query-параметр layout;
 * 3) fallback "menu".
 */
function resolveLayoutMode() {
    const loadMoreButton = document.getElementById("catalog-load-more-btn");
    const layoutFromButton = loadMoreButton?.dataset.layout;
    if (layoutFromButton === "sidebar" || layoutFromButton === "menu") {
        return layoutFromButton;
    }

    const layoutFromUrl = new URLSearchParams(window.location.search).get("layout");
    return layoutFromUrl === "sidebar" ? "sidebar" : "menu";
}

/**
 * Очищает адресную строку от технических query-параметров фильтров каталога.
 *
 * Почему это полезно:
 * - пользователь не видит "разрастающийся" URL с фильтрами;
 * - адрес страницы выглядит чище;
 * - мы оставляем в URL только то, что действительно имеет смысл для навигации пользователя
 *   (например, layout), а не внутренние технические параметры фильтрации.
 *
 * Важно:
 * - это влияет только на ВИДИМЫЙ URL в браузере;
 * - сервер уже успел получить нужные query-параметры и отрендерить правильные данные,
 *   поэтому очистка адресной строки ничего не ломает.
 */
function sanitizeCatalogVisibleUrl() {
    const currentUrl = new URL(window.location.href);
    let wasChanged = false;

    CATALOG_FILTER_QUERY_KEYS.forEach((paramName) => {
        if (!currentUrl.searchParams.has(paramName)) return;
        currentUrl.searchParams.delete(paramName);
        wasChanged = true;
    });

    if (!wasChanged) return;

    const normalizedSearch = currentUrl.searchParams.toString();
    const cleanUrl = `${currentUrl.pathname}${normalizedSearch ? `?${normalizedSearch}` : ""}${currentUrl.hash}`;
    window.history.replaceState(window.history.state, "", cleanUrl);
}

/**
 * Инициализирует модалку фильтров каталога.
 *
 * Что уже реализовано в рамках 1-го этапа:
 * - фильтр "Вид консультации" (Индивидуальная / Парная).
 *
 * Что важно по UX:
 * - пользователь выбирает значение в модалке;
 * - по кнопке "Показать результаты" страница перезагружается с query-параметром;
 * - выбранный фильтр живет в URL текущего сценария каталога, а не в server-side session.
 */
function initCatalogFiltersModal() {
    const modal = document.getElementById("filter-modal");
    const modalOverlay = document.getElementById("filter-modal-overlay");
    const modalTitle = document.getElementById("modal-title");
    const modalContent = document.getElementById("modal-content");
    const closeButton = document.getElementById("filter-modal-close-btn");
    const applyButton = document.getElementById("filter-modal-apply-btn");
    const filterButtons = document.querySelectorAll("[data-filter-chip]");

    if (
        !modal ||
        !modalOverlay ||
        !modalTitle ||
        !modalContent ||
        !closeButton ||
        !applyButton ||
        !filterButtons.length
    ) {
        return;
    }
    let openedFilterName = null;

    /**
     * Закрывает модалку и возвращает скролл основной странице.
     */
    function closeModal() {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
        document.body.style.overflow = "";
    }

    /**
     * Открывает модалку для выбранного фильтра.
     */
    function openModal(filterName) {
        openedFilterName = filterName;
        modalTitle.textContent = filterName;
        renderModalContent(filterName);
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        document.body.style.overflow = "hidden";
    }

    /**
     * Рендерит контент модалки для конкретного фильтра.
     *
     * На этом этапе детально поддерживаем только "Вид консультации".
     */
    function renderModalContent(filterName) {
        if (filterName !== "Вид консультации") {
            modalContent.innerHTML = `
                <p class="text-sm text-gray-500 leading-relaxed">
                    Этот фильтр будет подключен на следующем шаге. Сейчас можно закрыть модалку.
                </p>
            `;
            applyButton.textContent = APPLY_RESULTS_LABEL;
            return;
        }

        const activeConsultationType = getActiveConsultationTypeFromDOM();
        const consultationTypeChoices = getConsultationTypeChoices();
        const individualLabel = consultationTypeChoices.individual || "Индивидуальная";
        const coupleLabel = consultationTypeChoices.couple || "Парная";

        modalContent.innerHTML = `
            <div class="space-y-4">
                <p class="text-sm text-gray-500 leading-relaxed">
                    Выберите формат консультации для фильтрации карточек.
                </p>
                <div id="catalog-consultation-block" class="grid grid-cols-2 gap-3 max-w-md">
                    <button type="button" data-value="individual" class="catalog-consultation-btn px-4 py-2 rounded-lg border text-base font-medium">
                        ${individualLabel}
                    </button>
                    <button type="button" data-value="couple" class="catalog-consultation-btn px-4 py-2 rounded-lg border text-base font-medium">
                        ${coupleLabel}
                    </button>
                </div>
                <div id="catalog-consultation-hidden-inputs" class="hidden"></div>
                <p class="text-xs text-gray-400">
                    Можно оставить оба варианта невыбранными — это режим "все специалисты".
                </p>
            </div>
        `;

        // Используем уже существующий multi-toggle модуль.
        // Новый параметр maxSelected=1 добавлен обратно-совместимо:
        // старые места использования не изменяются, а здесь мы получаем режим
        // "выбран 1 вариант" или "не выбран ни один".
        initMultiToggle({
            containerSelector: "#catalog-consultation-block",
            buttonSelector: ".catalog-consultation-btn",
            hiddenInputsContainerSelector: "#catalog-consultation-hidden-inputs",
            inputName: "consultation_type",
            initialValues: activeConsultationType ? [activeConsultationType] : [],
            maxSelected: 1,
        });

        renderApplyButtonWithCount(applyButton, getModalSelectedConsultationType());

        const consultationBlock = document.getElementById("catalog-consultation-block");
        if (consultationBlock) {
            consultationBlock.addEventListener("click", (event) => {
                if (!event.target.closest(".catalog-consultation-btn")) return;

                // Ждем пока initMultiToggle обновит hidden-input и классы,
                // и только после этого пересчитываем текст кнопки.
                window.requestAnimationFrame(() => {
                    renderApplyButtonWithCount(applyButton, getModalSelectedConsultationType());
                });
            });
        }
    }

    /**
     * Применяет фильтр по кнопке "Показать результаты".
     *
     * Поведение:
     * - для реализованного фильтра "Вид консультации" перезагружаем страницу с query;
     * - для остальных фильтров пока просто закрываем модалку.
     */
    function applyCurrentFilter() {
        if (openedFilterName !== "Вид консультации") {
            closeModal();
            return;
        }

        const selectedValue = getModalSelectedConsultationType();
        const nextUrl = new URL(resolveCatalogEndpoint(), window.location.origin);
        const layoutMode = resolveLayoutMode();

        if (layoutMode === "sidebar" || layoutMode === "menu") {
            nextUrl.searchParams.set("layout", layoutMode);
        }

        // Если кнопки не активны, удаляем consultation_type и возвращаемся
        // к состоянию "все психологи".
        if (selectedValue) {
            nextUrl.searchParams.set("consultation_type", selectedValue);
        } else {
            nextUrl.searchParams.delete("consultation_type");
        }

        window.location.assign(nextUrl.toString());
    }

    filterButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const filterName = button.dataset.filterName || "Фильтр";
            openModal(filterName);
        });
    });

    modalOverlay.addEventListener("click", closeModal);
    closeButton.addEventListener("click", closeModal);
    applyButton.addEventListener("click", applyCurrentFilter);

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.classList.contains("hidden")) {
            closeModal();
        }
    });
}

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
    const consultationType = normalizeConsultationType(loadMoreButton.dataset.consultationType);

    return {
        layout_mode: layoutMode,
        current_page: currentPage,
        order_key: randomOrderKey,
        consultation_type: consultationType,
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
        const consultationType = normalizeConsultationType(loadMoreButton.dataset.consultationType);

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
            if (consultationType) {
                params.append("consultation_type", consultationType);
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

    sanitizeCatalogVisibleUrl();
    renderCurrentPageIndicator(initialPage, totalPages);

    initCatalogFiltersModal();
    initCardTabs();
    initCatalogStatePersistence();
    initLoadMore();
    initScrollToTopButton();
});
