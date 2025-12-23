import { pluralizeRu } from "../utils/pluralize_ru.js";

// ===== Вспомогательные функции =====

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


// ===== ЗАГРУЗКА ДАННЫХ: инфо психолога (имя, стоимость), бронируемый слот, добавление карты и подтверждение =====

const API_URL = "/aggregator/api/match-psychologists/";
const STORAGE_KEY = "selectedPsychologistId";

export async function initAddAppointmentAndPaymentCard() {
    const selectedId = sessionStorage.getItem(STORAGE_KEY);

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

        renderAddAppointmentAndPaymentCard(psychologist);

    } catch (error) {
        console.error("Ошибка при загрузке данных психолога:", error);
    }
}

function renderAddAppointmentAndPaymentCard(ps) {
    const container = document.getElementById("payment-psychologist-summary");
    if (!container) return;

    const sessionLabel = formatSessionLabel(ps.session_type);
    const priceLabel = formatPrice(ps.price);

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
                    Дата и время: <strong>20 декабря в 21:00 (четверг)</strong>
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
