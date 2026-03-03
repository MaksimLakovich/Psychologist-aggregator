import { initCollapsibleTopicGroups } from "./collapsible_topics_list.js";
import { resolveCatalogTopicTypeLabel } from "./catalog_filter_topic_type.js";

/**
 * Фильтр каталога "Симптомы".
 *
 * Бизнес-задача этого файла:
 * - показать пользователю модалку со сгруппированными симптомами и запросами;
 * - понять, какие темы пользователь выбрал для поиска психолога;
 * - согласовать фильтр "Симптомы" с фильтром "Вид консультации";
 * - передать странице каталога готовые функции для preview-count, применения фильтра и подсветки кнопки фильтра.
 */

export const CATALOG_TOPICS_FILTER_KEY = "topic_ids";
export const CATALOG_TOPICS_FILTER_NAME = "Симптомы";

// Кешируем подготовленные данные тем, чтобы не читать один и тот же json_script много раз за жизнь страницы.
let cachedTopicsByType = null;

// Кешируем словарь "topic_id -> вид консультации", чтобы быстро согласовывать фильтр "Симптомы" с фильтром "Вид консультации".
let cachedTopicIdToTypeMap = null;

// Читает с backend уже сгруппированные темы для модалки фильтра "Симптомы".
// Простыми словами: именно отсюда берем все разделы, группы и названия тем, которые показываем пользователю.
export function getCatalogTopicsByType({ readJsonScript }) {
    if (cachedTopicsByType !== null) {
        return cachedTopicsByType;
    }

    const rawTopics = readJsonScript("catalog-topics-by-type-data", {});
    cachedTopicsByType = rawTopics && typeof rawTopics === "object" ? rawTopics : {};
    return cachedTopicsByType;
}

// Приводит выбранные topic-id к чистому и безопасному виду.
// Простыми словами: оставляем только корректные id тем, убираем дубли и получаем предсказуемый набор значений для каталога и backend.
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

// Строит быстрый словарь "topic_id -> к какому виду консультации относится тема".
// Это нужно, чтобы фильтр "Симптомы" не оставлял темы, которые противоречат уже выбранному фильтру "Вид консультации".
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

// Оставляет только те темы, которые подходят выбранному виду консультации.
// Если фильтр "Вид консультации" не выбран, ничего не отбрасываем и оставляем все отмеченные темы.
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

// Проверяет, применен ли сейчас фильтр "Симптомы" в каталоге.
// Если функция возвращает true, страница понимает, что кнопка фильтра "Симптомы" должна подсветиться как активная.
export function isCatalogTopicsFilterActive(filters) {
    return normalizeCatalogTopicIds(filters?.topic_ids).length > 0;
}

// Читает из открытой модалки, какие симптомы пользователь отметил чекбоксами прямо сейчас.
// Это нужно и для применения фильтра, и для предварительного подсчета количества найденных специалистов.
export function getCatalogTopicsModalValues() {
    const checkboxes = document.querySelectorAll("#catalog-topic-groups-root .catalog-topic-checkbox:checked");
    return normalizeCatalogTopicIds(Array.from(checkboxes).map((checkbox) => checkbox.value));
}

// Определяет, какие разделы тем нужно показать пользователю в модалке.
// Если уже выбран фильтр "Вид консультации", показываем только подходящие темы; если не выбран, показываем все доступные разделы.
function getVisibleTopicTypeLabels({ catalogRuntimeState, readJsonScript }) {
    const selectedConsultationType = catalogRuntimeState.filters.consultation_type;
    const selectedTopicTypeLabel = resolveCatalogTopicTypeLabel(selectedConsultationType, { readJsonScript });
    const topicsByType = getCatalogTopicsByType({ readJsonScript });

    if (selectedTopicTypeLabel && topicsByType[selectedTopicTypeLabel]) {
        return [selectedTopicTypeLabel];
    }

    return Object.keys(topicsByType);
}

// Собирает HTML содержимого модалки фильтра "Симптомы".
// Простыми словами: превращает подготовленные backend-данные в удобный список групп и чекбоксов, который пользователь видит в интерфейсе.
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
                    <span class="text-sm sm:text-base font-medium text-gray-900">${escapeHtml(topic.name)}</span>
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
        ? "Показаны темы только для выбранного вида консультации"
        : "Можно выбрать темы как для индивидуальной, так и для парной консультации";

    return `
        <div class="space-y-4">
            <p class="text-sm text-gray-500 leading-relaxed">
                Выберите симптомы и запросы, с которыми должен работать психолог
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

// Собирает временное состояние фильтров только для preview-count в кнопке "Показать результаты".
// Простыми словами: пользователь еще не применил фильтр к каталогу, но мы уже можем посчитать, сколько специалистов будет найдено при текущем выборе чекбоксов.
export function buildCatalogTopicsTentativeFilters({
    catalogRuntimeState,
    normalizeCatalogFilters,
}) {
    return normalizeCatalogFilters({
        ...catalogRuntimeState.filters,
        topic_ids: getCatalogTopicsModalValues(),
    });
}

// Рисует модалку фильтра "Симптомы" и подключает ее поведение.
// Бизнес-смысл: показать пользователю все нужные группы тем, дать отмечать чекбоксы и после каждого изменения пересчитывать preview-count.
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

    // Для каталога показываем все темы группы сразу, поэтому visibleCount=0.
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
