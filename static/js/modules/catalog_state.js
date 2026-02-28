/**
 * Общий модуль для хранения временного состояния каталога психологов.
 *
 * Почему вынесено отдельно:
 * - каталог и detail-страница должны работать с одним и тем же форматом данных;
 * - когда фильтров станет 8, хранить такую логику прямо внутри page-файлов станет тяжело;
 * - так проще менять формат состояния в одном месте.
 *
 * Что именно считаем состоянием каталога:
 * - layout_mode: каталог открыт с sidebar или без него;
 * - current_page: до какой страницы пользователь уже догрузил карточки;
 * - order_key: по какому ключу сейчас перемешан каталог;
 * - anchor: к какой карточке нужно вернуться после detail;
 * - filters: объект со всеми временными фильтрами каталога;
 * - scroll_y: запасная позиция прокрутки для fallback-возврата;
 * - updated_at: когда состояние обновили в последний раз.
 */

/**
 * Ключ для основного состояния каталога.
 *
 * Суффикс "_v2" означает новую версию формата.
 * Это полезно, потому что раньше фильтры лежали в другом виде,
 * и старые записи в storage не должны мешать новой архитектуре.
 */
export const CATALOG_STATE_STORAGE_KEY = "psychologist_catalog_state_v2";

/**
 * Отдельный флаг "нужно восстановить каталог после detail".
 *
 * Зачем он нужен:
 * - состояние каталога может еще лежать в sessionStorage;
 * - но восстанавливать его нужно НЕ всегда, а только когда пользователь
 *   действительно возвращается из detail обратно в каталог.
 */
export const CATALOG_RESTORE_FLAG_STORAGE_KEY = "psychologist_catalog_restore_pending_v1";

/**
 * Срок жизни сохраненного состояния: 6 часов.
 *
 * Это страховка от слишком старых данных в sessionStorage.
 */
export const CATALOG_STATE_TTL_MS = 1000 * 60 * 60 * 6;

/**
 * Преобразует входное значение в целое число > 0.
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
 * Это важно для order_key, потому что он может быть равен 0.
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
 * - null, если данных нет, формат сломан или TTL истек.
 */
export function readCatalogState() {
    try {
        const rawState = window.sessionStorage.getItem(CATALOG_STATE_STORAGE_KEY);
        if (!rawState) return null;

        const parsedState = JSON.parse(rawState);
        if (!parsedState || typeof parsedState !== "object") return null;

        const updatedAt = toPositiveInt(parsedState.updated_at, null);
        if (updatedAt && Date.now() - updatedAt > CATALOG_STATE_TTL_MS) {
            clearCatalogState();
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
 * Любые ошибки storage проглатываем мягко,
 * чтобы не ломать основной пользовательский сценарий.
 */
export function writeCatalogState(state) {
    try {
        window.sessionStorage.setItem(CATALOG_STATE_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
        // В некоторых браузерных режимах storage может быть недоступен.
        // В таком случае просто пропускаем запись.
    }
}

/**
 * Полностью удаляет сохраненное состояние каталога.
 *
 * Используем это, когда пользователь открыл каталог заново,
 * а не вернулся в него из detail.
 */
export function clearCatalogState() {
    try {
        window.sessionStorage.removeItem(CATALOG_STATE_STORAGE_KEY);
    } catch (error) {
        // Ошибки очистки не должны ломать страницу.
    }
}

/**
 * Ставит флаг "после detail нужно восстановить каталог".
 *
 * Важно:
 * - этот флаг НЕ означает, что каталог надо восстанавливать всегда;
 * - он ставится только в момент осознанного возврата из detail в каталог.
 */
export function markCatalogRestorePending() {
    try {
        window.sessionStorage.setItem(CATALOG_RESTORE_FLAG_STORAGE_KEY, "1");
    } catch (error) {
        // Ошибки storage пропускаем.
    }
}

/**
 * Забирает и сразу удаляет флаг восстановления каталога.
 *
 * Простыми словами:
 * - если флаг был, возвращаем true и тут же его убираем;
 * - если флага не было, возвращаем false.
 *
 * Это поведение "одноразовое", чтобы старый флаг не срабатывал повторно.
 */
export function consumeCatalogRestorePending() {
    try {
        const isPending = window.sessionStorage.getItem(CATALOG_RESTORE_FLAG_STORAGE_KEY) === "1";
        window.sessionStorage.removeItem(CATALOG_RESTORE_FLAG_STORAGE_KEY);
        return isPending;
    } catch (error) {
        return false;
    }
}
