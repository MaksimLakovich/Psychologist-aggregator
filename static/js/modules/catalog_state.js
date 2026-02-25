/**
 * Общий модуль для хранения/чтения состояния каталога психологов в sessionStorage.
 *
 * Почему вынесено в отдельный файл:
 * - чтобы не дублировать один и тот же код в нескольких файлах: psychologist_catalog.js, psychologist_catalog_detail.js;
 * - чтобы любые будущие изменения делать в одном месте.
 *
 * Что именно считаем "состоянием каталога":
 * - layout_mode: как открыт каталог ("menu" или "sidebar");
 * - current_page: до какой страницы пользователь догрузил карточки;
 * - order_key: ключ стабильного случайного порядка карточек;
 * - anchor: slug выбранной карточки для возврата к нужному месту;
 * - updated_at: когда состояние последний раз обновили.
 */

/**
 * Ключ, под которым состояние лежит в sessionStorage.
 *
 * Суффикс "_v1" = версия формата данных.
 * Пример:
 * - сегодня мы храним поля A,B,C и ключ называется "..._v1";
 * - завтра меняем формат (добавили/удалили поля) и можем перейти на "..._v2",
 *   чтобы не конфликтовать со старым форматом.
 */
export const CATALOG_STATE_STORAGE_KEY = "psychologist_catalog_state_v1";

/**
 * Срок жизни сохраненного состояния: 6 часов.
 *
 * 1000 * 60 * 60 * 6 = 6 часов в миллисекундах.
 * Зачем нужно:
 * - чтобы пользователь не получил "слишком старое" состояние спустя долгий перерыв;
 * - чтобы периодически очищать storage от устаревших данных.
 */
export const CATALOG_STATE_TTL_MS = 1000 * 60 * 60 * 6;

/**
 * Преобразует входное значение в целое число > 0.
 *
 * Пример:
 * - "3" -> 3
 * - "0" -> fallback
 * - "abc" -> fallback
 */
export function toPositiveInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed > 0) {
        return parsed;
    }
    return fallback;
}

/**
 * Преобразует входное значение в целое число >= 0.
 *
 * Отличие от toPositiveInt:
 * - здесь "0" — валидное число.
 * Это важно для order_key, потому что ключ может быть равен 0.
 */
export function toNonNegativeInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed >= 0) {
        return parsed;
    }
    return fallback;
}

/**
 * Читает состояние каталога из sessionStorage.
 *
 * Возвращает:
 * - объект состояния, если данные валидны и не истекли;
 * - null, если данных нет / формат битый / TTL истек.
 */
export function readCatalogState() {
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
 * Пишет состояние каталога в sessionStorage.
 *
 * Важно:
 * - любые ошибки чтения/записи storage не должны ломать UI,
 *   поэтому здесь "мягкая" обработка ошибок.
 */
export function writeCatalogState(state) {
    try {
        window.sessionStorage.setItem(CATALOG_STATE_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
        // В некоторых режимах браузера storage может быть недоступен.
        // Просто пропускаем запись и не блокируем сценарий пользователя.
    }
}
