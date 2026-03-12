/**
 * Бизнес-смысл модуля:
 * Клиент не должен случайно перейти к оплате без выбранного времени.
 * Модуль централизованно управляет:
 * - хранением выбранного слота;
 * - доступностью кнопки оплаты и шага "Запись и оплата".
 */


// Ключ в sessionStorage для выбранного слота (переход на оплату)
const SELECTED_APPOINTMENT_SLOT_KEY = "selectedAppointmentSlot";

// На входе в страницу сбрасываем прошлый слот и блокируем переход к оплате
export function initSessionChoiceState() {
    sessionStorage.removeItem(SELECTED_APPOINTMENT_SLOT_KEY);
    updatePaymentStepLink(false);
}

// Сохраняем выбранный слот в sessionStorage для последующей страницы оплаты
export function setSelectedAppointmentSlot(psId, slot) {
    if (!slot) {
        sessionStorage.removeItem(SELECTED_APPOINTMENT_SLOT_KEY);
        return;
    }

    sessionStorage.setItem(
        SELECTED_APPOINTMENT_SLOT_KEY,
        JSON.stringify({
            psychologistId: String(psId),
            slot,
        })
    );
}

// Формируем целевой URL следующего шага booking-flow с уже выбранными параметрами.
export function buildPaymentStepUrl(baseUrl, { psychologistId, slotStartIso, consultationType }) {
    if (!baseUrl || !psychologistId || !slotStartIso || !consultationType) {
        return null;
    }

    const url = new URL(baseUrl, window.location.origin);
    url.searchParams.set("specialist_profile_id", String(psychologistId));
    url.searchParams.set("slot_start_iso", slotStartIso);
    url.searchParams.set("consultation_type", consultationType);

    return `${url.pathname}${url.search}${url.hash}`;
}

// Функция для управления АКТИВНО/НЕАКТИВНО в блоке "ШАГИ" чтоб нельзя было перейти на страницу "Запись" без выбранного слота
function updatePaymentStepLink(isEnabled, targetHref = null) {
    const link = document.querySelector("[data-payment-step-link]");
    if (!link) return;

    if (!link.dataset.href) {
        link.dataset.href = link.getAttribute("href") || "";
    }

    if (targetHref) {
        link.dataset.href = targetHref;
    }

    if (isEnabled) {
        link.setAttribute("href", link.dataset.href);
        link.classList.remove("pointer-events-none", "opacity-50");
        link.setAttribute("aria-disabled", "false");
        return;
    }

    link.setAttribute("href", "#");
    link.classList.add("pointer-events-none", "opacity-50");
    link.setAttribute("aria-disabled", "true");
}

// Синхронно обновляем ссылку шага "Запись и оплата".
// Если слот выбран, шаг становится активным и ведет на конкретный URL payment-card.
// Если слот не выбран, шаг снова блокируется, чтобы клиент не мог перейти дальше раньше времени.
export function updatePaymentStepTarget(targetHref) {
    updatePaymentStepLink(Boolean(targetHref), targetHref);
}

// Функция для управления активностью и синхронно управляем доступностью шага оплаты + формирования подписи в КНОПКЕ: "Выбрать время сессии"
export function updateChooseButton(selectedSlotLabel) {
    const btn = document.querySelector("[data-choose-session-btn]");
    if (!btn) return;

    if (selectedSlotLabel) {
        btn.disabled = false;
        btn.textContent = `Выбрать ${selectedSlotLabel}`;
        btn.classList.remove("bg-gray-300", "text-gray-500", "cursor-not-allowed");
        btn.classList.add("bg-indigo-500", "text-white", "hover:bg-indigo-900");
        updatePaymentStepLink(true);
        return;
    }

    btn.disabled = true;
    btn.textContent = "Выбрать время сессии";
    btn.classList.add("bg-gray-300", "text-gray-500", "cursor-not-allowed");
    btn.classList.remove("bg-indigo-500", "text-white", "hover:bg-indigo-900");
    updatePaymentStepLink(false);
}
