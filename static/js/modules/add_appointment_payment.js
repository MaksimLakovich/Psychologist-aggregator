import { pluralizeRu } from "../utils/pluralize_ru.js";


/* ============================================================================
 * ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
 * ========================================================================== */


// 1) Логика отображения PRICE в зависимости от "individual/couple"
export function formatSessionLabel(sessionType) {
    return sessionType === "couple"
        ? "Сессия · 1,5 часа"
        : "Сессия · 50 минут";
}

// 2) Убираем копейки и формируем цену с указанием валюты
export function formatPrice(price) {
    return `${Number(price.value).toFixed(0)} ${price.currency}`;
}


/* ============================================================================
 * ИНИЦИАЛИЗАЦИЯ
 * Загрузка данных: инфо психолога (имя, стоимость), бронируемый слот, добавление карты и подтверждение
 * ========================================================================== */


const API_URL = "/aggregator/api/match-psychologists/";
const STORAGE_KEY = "selectedPsychologistId";
const SELECTED_APPOINTMENT_SLOT_KEY = "selectedAppointmentSlot";

export async function initAddAppointmentAndPaymentCard() {
    const selectedId = sessionStorage.getItem(STORAGE_KEY);
    let selectedSlot = null;

    try {
        const rawSlot = sessionStorage.getItem(SELECTED_APPOINTMENT_SLOT_KEY);
        if (rawSlot) {
            const parsed = JSON.parse(rawSlot);
            if (parsed && String(parsed.psychologistId) === String(selectedId)) {
                selectedSlot = parsed.slot || null;
            }
        }
    } catch (error) {
        console.warn("Не удалось прочитать выбранный слот:", error);
    }

    if (!selectedId) {
        console.warn("Психолог не выбран");
        return;
    }

    try {
        const response = await fetch(API_URL);
        const data = await response.json();

        const psychologist = data.items?.find(
            ps => String(ps.id) === String(selectedId)
        );

        if (!psychologist) {
            console.warn("Выбранный психолог не найден");
            return;
        }

        renderAddAppointmentAndPaymentCard(psychologist, selectedSlot);

    } catch (error) {
        console.error("Ошибка при загрузке данных психолога:", error);
    }
}

// 1) Функция для формирования инфо по выбранному СЛОТУ (например: "Дата и время: 9 февраля 18:00 (понедельник)")
function formatAppointmentSlot(slot) {
    if (!slot) return "Слот не выбран";

    let dateObj = null;
    if (slot.start_iso) {
        dateObj = new Date(slot.start_iso);
    } else if (slot.day && slot.start_time) {
        dateObj = new Date(`${slot.day}T${slot.start_time}`);
    }
    if (!dateObj || Number.isNaN(dateObj.getTime())) {
        return "Слот не выбран";
    }

    const datePart = new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "long",
    }).format(dateObj);

    const timePart = new Intl.DateTimeFormat("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
    }).format(dateObj);

    const weekdayLong = new Intl.DateTimeFormat("ru-RU", {
        weekday: "long",
    }).format(dateObj).toLowerCase();

    return `${datePart} ${timePart} (${weekdayLong})`;
}

// 2) Функция для формирования HTML-шаблона
function renderAddAppointmentAndPaymentCard(ps, selectedSlot) {
    const container = document.getElementById("payment-psychologist-summary");
    if (!container) return;

    const sessionLabel = formatSessionLabel(ps.session_type);
    const priceLabel = formatPrice(ps.price);

    const slotLabel = formatAppointmentSlot(selectedSlot);

    container.innerHTML = `
        <div class="flex flex-col items-center text-center gap-4 pb-0">

            <img
                src="${ps.photo}"
                alt="Фото психолога"
                class="h-20 w-20 rounded-full object-cover shadow"
            />

            <div>
                <p class="text-2xl font-semibold text-gray-900 pb-8">
                    ${ps.full_name}
                </p>

                <p class="text-lg text-gray-900 mt-0">
                    ${sessionLabel} · <strong>${priceLabel}</strong>
                </p>

                <p class="text-lg text-gray-900 mt-2 pb-8">
                    Дата и время: <strong>${slotLabel}</strong>
                </p>
            </div>

            <div class="w-full mt-0">
                <label class="block text-lg font-medium text-gray-900 mb-1">
                    Тип карты
                </label>
                <select
                    class="w-full rounded-lg bg-indigo-100 border-gray-300 focus:ring-indigo-500 focus:border-indigo-500"
                >
                    <option>Карта РФ или МИР</option>
                    <option>Иностранная карта</option>
                </select>
            </div>

        </div>
    `;
}
