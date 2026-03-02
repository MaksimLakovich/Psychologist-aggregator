import { initCollapsibleTopicGroups } from "./collapsible_topics_list.js";
import { resolveCatalogTopicTypeLabel } from "./catalog_filter_topic_type.js";

/**
 * Модуль фильтра каталога "Симптомы".
 *
 * Бизнес-задача этого файла:
 * - отрисовать модалку сгруппированных тем с чекбоксами;
 * - прочитать и нормализовать выбранные topic-id;
 * - переиспользовать уже существующую UI-логику grouped topics;
 * - дать странице каталога готовые функции для preview и применения фильтра.
 */

export const CATALOG_TOPICS_FILTER_KEY = "topic_ids";
export const CATALOG_TOPICS_FILTER_NAME = "Симптомы";

let cachedTopicsByType = null;
let cachedTopicIdToTypeMap = null;

/**
 * Читает сгруппированные темы из json_script.
 *
 * Это данные, которые backend уже подготовил для модалки фильтра.
 */
export function getCatalogTopicsByType({ readJsonScript }) {
    if (cachedTopicsByType !== null) {
        return cachedTopicsByType;
    }

    const rawTopics = readJsonScript("catalog-topics-by-type-data", {});
    cachedTopicsByType = rawTopics && typeof rawTopics === "object" ? rawTopics : {};
    return cachedTopicsByType;
}

/**
 * Строит быстрый словарь "topic_id -> вид консультации".
 *
 * Это нужно, чтобы при выбранном фильтре "Вид консультации"
 * автоматически отбрасывать темы другого типа.
 */
export function getCatalogTopicIdToTypeMap({ readJsonScript }) {
    if (cachedTopicIdToTypeMap !== null) {
        return cachedTopicIdToTypeMap;
    }

    const topicIdToTypeMap = {};
    const topicsByType = getCatalogTopicsByType({ readJsonScript });

    Object.entries(topicsByType).forEach(([topicTypeLabel, groups]) => {
        Object.values(groups || {}).forEach((topics) => {
            (topics || []).forEach((topic) => {
                if (!topic?.id) return;
                topicIdToTypeMap[String(topic.id)] = topicTypeLabel;
            });
        });
    });

    cachedTopicIdToTypeMap = topicIdToTypeMap;
    return cachedTopicIdToTypeMap;
}

/**
 * Нормализует список topic-id.
 *
 * Что делаем:
 * - оставляем только положительные целые id;
 * - убираем дубли;
 * - возвращаем список строк в стабильном порядке.
 */
export function normalizeCatalogTopicIds(rawValues) {
    if (!Array.isArray(rawValues)) return [];

    const normalizedTopicIds = [];
    const seenTopicIds = new Set();

    rawValues.forEach((rawValue) => {
        const parsedValue = Number.parseInt(String(rawValue), 10);
        if (!Number.isInteger(parsedValue) || parsedValue <= 0) return;

        const normalizedValue = String(parsedValue);
        if (seenTopicIds.has(normalizedValue)) return;

        seenTopicIds.add(normalizedValue);
        normalizedTopicIds.push(normalizedValue);
    });

    return normalizedTopicIds;
}

/**
 * Оставляет только те темы, которые соответствуют выбранному виду консультации.
 *
 * Если фильтр "Вид консультации" не выбран,
 * возвращаем все выбранные темы без изменений.
 */
export function filterCatalogTopicIdsByConsultationType({
    topicIds,
    consultationType,
    readJsonScript,
}) {
    const normalizedTopicIds = normalizeCatalogTopicIds(topicIds);
    const topicTypeLabel = resolveCatalogTopicTypeLabel(consultationType, { readJsonScript });
    if (!topicTypeLabel) return normalizedTopicIds;

    const topicIdToTypeMap = getCatalogTopicIdToTypeMap({ readJsonScript });
    return normalizedTopicIds.filter((topicId) => topicIdToTypeMap[topicId] === topicTypeLabel);
}

/**
 * Проверяет, активен ли фильтр "Симптомы".
 *
 * Если выбран хотя бы один topic-id, чип фильтра на странице должен подсветиться.
 */
export function isCatalogTopicsFilterActive(filters) {
    return normalizeCatalogTopicIds(filters?.topic_ids).length > 0;
}

/**
 * Читает выбранные topic-id из открытой модалки.
 */
export function getCatalogTopicsModalValues() {
    const checkboxes = document.querySelectorAll("#catalog-topic-groups-root .catalog-topic-checkbox:checked");
    return normalizeCatalogTopicIds(Array.from(checkboxes).map((checkbox) => checkbox.value));
}

/**
 * Возвращает список разделов тем, которые надо показать в модалке.
 *
 * Если выбран вид консультации, показываем только его темы.
 * Если вид не выбран, показываем темы обоих видов.
 */
function getVisibleTopicTypeLabels({ catalogRuntimeState, readJsonScript }) {
    const selectedConsultationType = catalogRuntimeState.filters.consultation_type;
    const selectedTopicTypeLabel = resolveCatalogTopicTypeLabel(selectedConsultationType, { readJsonScript });
    const topicsByType = getCatalogTopicsByType({ readJsonScript });

    if (selectedTopicTypeLabel && topicsByType[selectedTopicTypeLabel]) {
        return [selectedTopicTypeLabel];
    }

    return Object.keys(topicsByType);
}

/**
 * Собирает HTML модалки фильтра "Симптомы".
 *
 * Здесь переиспользуем уже знакомую структуру grouped topics:
 * - заголовок группы;
 * - список чекбоксов;
 * - кнопка "Ещё".
 */
export function buildTopicsModalHtml({
    selectedTopicIds,
    catalogRuntimeState,
    escapeHtml,
    readJsonScript,
}) {
    const topicsByType = getCatalogTopicsByType({ readJsonScript });
    const visibleTopicTypeLabels = getVisibleTopicTypeLabels({ catalogRuntimeState, readJsonScript });

    if (!visibleTopicTypeLabels.length) {
        return `
            <p class="text-sm text-gray-500 leading-relaxed">
                Темы пока не добавлены.
            </p>
        `;
    }

    const sectionsHtml = visibleTopicTypeLabels.map((topicTypeLabel) => {
        const groupedTopics = topicsByType[topicTypeLabel] || {};
        const groupsHtml = Object.entries(groupedTopics).map(([groupName, topics]) => {
            const itemsHtml = (topics || []).map((topic) => `
                <label class="topic-item flex items-center gap-3 p-1 rounded-md hover:bg-gray-50 transition">
                    <input
                        type="checkbox"
                        value="${topic.id}"
                        class="catalog-topic-checkbox w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                        ${selectedTopicIds.includes(String(topic.id)) ? "checked" : ""}
                    >
                    <span class="text-base font-medium text-gray-900">${escapeHtml(topic.name)}</span>
                </label>
            `).join("");

            return `
                <div class="topic-group mb-1 pb-4">
                    <p class="block mb-2 text-lg font-medium text-indigo-500">
                        <strong>${escapeHtml(groupName)}</strong>
                    </p>
                    <div class="topics-group grid grid-cols-1 sm:grid-cols-2">
                        ${itemsHtml || '<p class="text-base text-gray-500">Темы не найдены.</p>'}
                    </div>
                    <button
                        type="button"
                        class="show-more-topics hidden mt-2 italic text-sm font-medium text-indigo-500 hover:text-indigo-900"
                    >
                        Ещё
                    </button>
                </div>
            `;
        }).join("");

        const typeTitleHtml = visibleTopicTypeLabels.length > 1 ? `
            <div class="pt-2 pb-1 border-b border-slate-100">
                <p class="text-sm font-black uppercase tracking-[0.2em] text-slate-400">${escapeHtml(topicTypeLabel)}</p>
            </div>
        ` : "";

        return `
            <section class="space-y-3">
                ${typeTitleHtml}
                ${groupsHtml || '<p class="text-sm text-gray-500">Темы не найдены.</p>'}
            </section>
        `;
    }).join("");

    const helperText = catalogRuntimeState.filters.consultation_type
        ? "Показаны темы только для выбранного вида консультации."
        : "Можно выбрать темы как для индивидуальной, так и для парной консультации.";

    return `
        <div class="space-y-4">
            <p class="text-sm text-gray-500 leading-relaxed">
                Выберите симптомы и запросы, с которыми должен работать психолог.
            </p>
            <div id="catalog-topic-groups-root" class="max-h-[28rem] overflow-y-auto pr-1 space-y-5">
                ${sectionsHtml}
            </div>
            <p class="text-xs text-gray-400">
                ${helperText}
            </p>
        </div>
    `;
}

/**
 * Собирает временное состояние фильтров для preview-count.
 *
 * Это нужно, когда пользователь отмечает чекбоксы в модалке,
 * но еще не нажал "Показать результаты".
 */
export function buildCatalogTopicsTentativeFilters({
    catalogRuntimeState,
    normalizeCatalogFilters,
}) {
    return normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        topic_ids: getCatalogTopicsModalValues(),
    });
}

/**
 * Рендерит модалку фильтра "Симптомы" и подключает ее поведение.
 *
 * На странице каталога показываем все темы группы сразу,
 * поэтому visibleCount=0 в reusable-модуле grouped topics.
 */
export function renderCatalogTopicsModal({
    modalContent,
    catalogRuntimeState,
    schedulePreviewRefresh,
    escapeHtml,
    readJsonScript,
}) {
    const selectedTopicIds = normalizeCatalogTopicIds(catalogRuntimeState.filters.topic_ids);
    modalContent.innerHTML = buildTopicsModalHtml({
        selectedTopicIds,
        catalogRuntimeState,
        escapeHtml,
        readJsonScript,
    });

    initCollapsibleTopicGroups({
        rootSelector: "#catalog-topic-groups-root",
        visibleCount: 0,
    });

    const topicsRoot = document.getElementById("catalog-topic-groups-root");
    if (!topicsRoot) return;

    topicsRoot.addEventListener("change", (event) => {
        if (!event.target.closest(".catalog-topic-checkbox")) return;
        schedulePreviewRefresh();
    });
}
