/**
 * Общее временное состояние каталога психологов.
 *
 * Бизнес-задача этого файла:
 * - хранить единый формат состояния каталога для страницы списка и detail-страницы;
 * - запоминать временные фильтры, текущую страницу, позицию возврата и служебные флаги;
 * - дать всем частям каталога один общий способ читать, писать и очищать это состояние.
 */

// Ключ для основного состояния каталога в sessionStorage.
// Суффикс "_v2" означает новую версию формата, чтобы старые данные не мешали текущей архитектуре.
export const CATALOG_STATE_STORAGE_KEY = "psychologist_catalog_state_v2";

// Отдельный флаг "нужно восстановить каталог после detail".
// Он нужен, чтобы не восстанавливать старое состояние каждый раз при обычном новом входе в каталог.
export const CATALOG_RESTORE_FLAG_STORAGE_KEY = "psychologist_catalog_restore_pending_v1";

// Максимальный срок жизни сохраненного состояния: 6 часов.
// Это защита от слишком старых данных в sessionStorage.
export const CATALOG_STATE_TTL_MS = 1000 * 60 * 60 * 6;

// Преобразует входное значение в целое число больше нуля.
// Используем это там, где 0 уже не является допустимым значением.
export function toPositiveInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed > 0) {
        return parsed;
    }
    return fallback;
}

// Преобразует входное значение в целое число больше или равно нулю.
// Это важно, например, для order_key, потому что у него 0 тоже может быть валидным значением.
export function toNonNegativeInt(value, fallback = null) {
    const parsed = Number.parseInt(String(value), 10);
    if (Number.isInteger(parsed) && parsed >= 0) {
        return parsed;
    }
    return fallback;
}

// Читает состояние каталога из sessionStorage.
// Если данных нет, они устарели или формат сломан, возвращаем null, чтобы каталог начал работу с чистого состояния.
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

// Записывает состояние каталога в sessionStorage.
// Если storage недоступен, просто молча пропускаем запись, чтобы не ломать основной сценарий пользователя.
export function writeCatalogState(state) {
    try {
        window.sessionStorage.setItem(CATALOG_STATE_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
        // В некоторых браузерных режимах storage может быть недоступен.
        // В таком случае просто пропускаем запись.
    }
}

// Полностью удаляет сохраненное состояние каталога.
// Используем это, когда пользователь открыл каталог заново, а не вернулся в него из detail.
export function clearCatalogState() {
    try {
        window.sessionStorage.removeItem(CATALOG_STATE_STORAGE_KEY);
    } catch (error) {
        // Ошибки очистки не должны ломать страницу.
    }
}

// Ставит одноразовый флаг "после detail нужно восстановить каталог".
// Само состояние каталога может храниться и дольше, но этот флаг говорит, что восстановление сейчас действительно нужно выполнить.
export function markCatalogRestorePending() {
    try {
        window.sessionStorage.setItem(CATALOG_RESTORE_FLAG_STORAGE_KEY, "1");
    } catch (error) {
        // Ошибки storage пропускаем.
    }
}

// Читает и сразу удаляет флаг восстановления каталога.
// Простыми словами: если пользователь действительно возвращается из detail, флаг срабатывает один раз и не остается висеть дальше.
export function consumeCatalogRestorePending() {
    try {
        const isPending = window.sessionStorage.getItem(CATALOG_RESTORE_FLAG_STORAGE_KEY) === "1";
        window.sessionStorage.removeItem(CATALOG_RESTORE_FLAG_STORAGE_KEY);
        return isPending;
    } catch (error) {
        return false;
    }
}
