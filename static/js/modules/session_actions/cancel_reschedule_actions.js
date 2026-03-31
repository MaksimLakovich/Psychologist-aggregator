import {
    formatSlotParts,
    renderScheduleList,
} from "../detail_card/detail_card_schedule.js";

/*
 * Общий смысл:
 * - этот модуль управляет двумя действиями клиента внутри детальной карточки встречи:
 *   1) отменой встречи;
 *   2) переносом встречи на другой доступный слот;
 * - JS здесь отвечает только за поведение интерфейса:
 *   - открыть/закрыть модальные окна;
 *   - не дать отправить пустую форму отмены;
 *   - загрузить доступные слоты специалиста для переноса;
 *   - дать клиенту выбрать новый слот и только потом разрешить отправку формы.
 *
 * Важно:
 * - реальная бизнес-логика отмены/переноса выполняется на backend;
 * - этот файл только помогает пользователю корректно пройти UI-сценарий.
 */

// Универсальный helper для работы с модальными окнами.
// Нужен, чтобы не дублировать один и тот же код для cancel-modal и reschedule-modal:
// открыть окно, закрыть по крестику, закрыть по клику на фон, закрыть по Escape
function bindModalVisibility({ modal, openButtonsSelector, closeButtonsSelector, onOpen }) {
    if (!modal) return;

    const openButtons = document.querySelectorAll(openButtonsSelector);
    const closeButtons = modal.querySelectorAll(closeButtonsSelector);

    // Полностью скрывает модальное окно из интерфейса
    const closeModal = () => {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    };

    // Показывает модальное окно.
    // Если для этого окна нужен дополнительный сценарий при открытии
    // (например, загрузить расписание специалиста), он выполняется через onOpen
    const openModal = async () => {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        if (typeof onOpen === "function") {
            await onOpen();
        }
    };

    openButtons.forEach(button => {
        button.addEventListener("click", openModal);
    });

    closeButtons.forEach(button => {
        button.addEventListener("click", closeModal);
    });

    modal.addEventListener("click", event => {
        if (event.target === modal) {
            closeModal();
        }
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && !modal.classList.contains("hidden")) {
            closeModal();
        }
    });
}

// Инициализация модального окна "Отменить встречу".
// UI-правило простое:
// - пока причина отмены пустая, кнопку отправки формы блокируем;
// - как только клиент вводит текст причины, кнопку разблокируем
function initCancelSessionModal() {
    const modal = document.getElementById("cancel-session-modal");
    const cancelReasonField = document.getElementById("id_cancel_reason");
    const submitButton = document.getElementById("cancel-session-submit");

    if (!modal || !cancelReasonField || !submitButton) return;

    // Синхронизирует доступность кнопки "Отменить встречу" с заполненностью причины отмены
    const syncButtonState = () => {
        submitButton.disabled = cancelReasonField.value.trim().length === 0;
    };

    cancelReasonField.addEventListener("input", syncButtonState);
    syncButtonState();

    bindModalVisibility({
        modal,
        openButtonsSelector: "[data-open-cancel-modal]",
        closeButtonsSelector: "[data-close-cancel-modal]",
    });
}

// Инициализация модального окна "Перенести встречу".
// Сценарий:
// - нужно загрузить актуальное расписание специалиста;
// - исключить из него текущее переносимое событие;
// - скрыть текущий уже выбранный слот, чтобы пользователь не выбрал его повторно;
// - разрешить отправку формы только после выбора нового слота
function initRescheduleSessionModal() {
    const modal = document.getElementById("reschedule-session-modal");
    const scheduleList = document.getElementById("reschedule-schedule-list");
    const slotStartIsoField = document.getElementById("id_slot_start_iso");
    const previousEventField = document.getElementById("id_previous_event_id");
    const submitButton = document.getElementById("reschedule-session-submit");

    if (!modal || !scheduleList || !slotStartIsoField || !previousEventField || !submitButton) {
        return;
    }

    const scheduleUrl = modal.dataset.scheduleUrl;
    const consultationType = modal.dataset.consultationType || "individual";
    const clientTimeZone = modal.dataset.clientTimezone || undefined;
    const currentSlotStartIso = modal.dataset.currentSlotStartIso || "";
    const defaultSubmitButtonText = "Перенести встречу";
    let selectedSlotLabel = "";

    // Кнопка "Перенести встречу" становится активной только когда:
    // - backend уже знает, какое старое событие переносим;
    // - пользователь выбрал новый слот
    const syncButtonState = () => {
        submitButton.disabled = !(previousEventField.value && slotStartIsoField.value);
        submitButton.textContent = selectedSlotLabel
            ? `Перенести встречу на ${selectedSlotLabel}`
            : defaultSubmitButtonText;
    };

    // Сбрасывает выбранный новый слот, если:
    // - модалка открылась заново;
    // - расписание не загрузилось;
    // - список слотов был пересчитан
    const resetSelectedSlot = () => {
        slotStartIsoField.value = "";
        selectedSlotLabel = "";
        syncButtonState();
    };

    // Отрисовывает список доступных слотов в правой части модального окна
    const renderSchedule = schedule => {
        scheduleList.innerHTML = renderScheduleList(schedule, slotStartIsoField.value || null);
    };

    // Формирует короткую человекочитаемую подпись выбранного слота для текста кнопки:
    // "1 апреля 19:00" вместо технического "2026-04-01 19:00".
    const buildSelectedSlotButtonLabel = slotStartIso => {
        const parts = formatSlotParts({ start_iso: slotStartIso }, clientTimeZone);
        if (!parts) {
            return "новое время";
        }

        return `${parts.datePart} ${parts.timePart}`;
    };

    // Загружает с backend актуальное расписание специалиста именно для сценария переноса.
    //
    // Что важно по бизнес-смыслу:
    // - backend возвращает доступные слоты по текущим правилам расписания специалиста;
    // - в запрос дополнительно передается previous_event_id как exclude_event_id,
    //   чтобы старое переносимое событие не блокировало само себя;
    // - текущий слот затем отдельно скрывается на frontend, чтобы клиент не выбрал то же самое время повторно
    const loadSchedule = async () => {
        if (!scheduleUrl) {
            scheduleList.innerHTML = `
                <div class="flex h-48 items-center justify-center text-sm font-medium text-rose-400">
                    Не удалось определить расписание специалиста для переноса
                </div>
            `;
            resetSelectedSlot();
            return;
        }

        scheduleList.innerHTML = `
            <div class="flex h-48 items-center justify-center text-sm font-medium text-zinc-400">
                Подгружаем доступные слоты...
            </div>
        `;
        resetSelectedSlot();

        try {
            // consultation_type нужен backend, чтобы построить доступные слоты
            // с учетом длительности и правил конкретного типа встречи
            const query = new URLSearchParams({
                consultation_type: consultationType,
            });

            // exclude_event_id говорит backend:
            // "не считай текущее старое событие занятым временем специалиста,
            // потому что именно его мы сейчас переносим"
            if (previousEventField.value) {
                query.set("exclude_event_id", previousEventField.value);
            }

            const response = await fetch(
                `${scheduleUrl}?${query.toString()}`,
                {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                },
            );

            if (!response.ok) {
                throw new Error("schedule_request_failed");
            }

            const payload = await response.json();

            // Из итогового списка убираем текущий слот,
            // чтобы в модалке остались только реально новые варианты времени
            const schedule = (payload.schedule || []).filter(slot => slot.start_iso !== currentSlotStartIso);

            renderSchedule(schedule);
        } catch (error) {
            scheduleList.innerHTML = `
                <div class="flex h-48 items-center justify-center text-sm font-medium text-rose-400">
                    Не удалось загрузить доступные слоты. Попробуйте открыть модальное окно еще раз
                </div>
            `;
            resetSelectedSlot();
        }
    };

    // Обработка выбора конкретного нового слота из списка.
    // Здесь UI:
    // - снимает выделение со старого выбора;
    // - подсвечивает новый выбор;
    // - сохраняет slot_start_iso в hidden-поле формы;
    // - обновляет текст "какой слот выбран";
    // - разблокирует кнопку отправки формы
    scheduleList.addEventListener("click", event => {
        const button = event.target.closest("button[data-slot-key]");
        if (!button) return;

        const slotKey = button.dataset.slotKey || "";
        const slotStartIso = button.dataset.startIso || slotKey;

        scheduleList.querySelectorAll("button[data-slot-key]").forEach(slotButton => {
            slotButton.classList.remove("bg-indigo-500", "text-white", "border-transparent", "hover:bg-indigo-500");
            slotButton.classList.add("bg-gray-100/70", "text-gray-500", "border-transparent", "hover:bg-gray-200/60");
        });

        button.classList.remove("bg-gray-100/70", "text-gray-500", "border-transparent", "hover:bg-gray-200/60");
        button.classList.add("bg-indigo-500", "text-white", "border-transparent", "hover:bg-indigo-500");

        slotStartIsoField.value = slotStartIso;
        selectedSlotLabel = buildSelectedSlotButtonLabel(slotStartIso);
        syncButtonState();
    });

    // При первой инициализации синхронизируем состояние кнопки до открытия модалки
    syncButtonState();

    bindModalVisibility({
        modal,
        openButtonsSelector: "[data-open-reschedule-modal]",
        closeButtonsSelector: "[data-close-reschedule-modal]",
        onOpen: loadSchedule,
    });
}

// Точка входа модуля после полной загрузки HTML-страницы.
// Инициализируем оба сценария: отмену и перенос встречи
document.addEventListener("DOMContentLoaded", () => {
    initCancelSessionModal();
    initRescheduleSessionModal();
});
