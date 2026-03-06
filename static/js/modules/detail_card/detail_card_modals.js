/**
 * Бизнес-смысл модуля:
 * Клиенту нужны дополнительные объяснения до оплаты:
 * - что включает подход психолога (модалка методов);
 * - на каких условиях оказывается услуга (модалка оферты).
 * Модуль централизует это поведение, чтобы и карточка подбора, и другие
 * страницы использовали одинаковую логику.
 */

let psychologistsProvider = () => [];

function getPsychologists() {
    const list = psychologistsProvider();
    return Array.isArray(list) ? list : [];
}

export function initDetailCardModals({ getPsychologistsList } = {}) {
    if (typeof getPsychologistsList === "function") {
        psychologistsProvider = getPsychologistsList;
    }

// МОДАЛКА ДЛЯ ОТОБРАЖАНЕИЯ ОПИСАНИЯ МЕТОДОВ
    window.openMethodsInfoModal = function (psychologistId) {
        const psychologists = getPsychologists();
        const ps = psychologists.find(item => item.id === psychologistId);
        if (!ps || !ps.methods?.length) return;

        const content = document.getElementById("methods-info-content");
        const modal = document.getElementById("methods-info-modal");
        if (!content || !modal) return;

        content.innerHTML = ps.methods.map(method => `
            <div>
                <h4 class="text-lg font-semibold text-gray-900">${method.name}</h4>
                <p class="mt-1 text-gray-700 leading-relaxed">${method.description || "Описание отсутствует"}</p>
            </div>
        `).join("");

        modal.classList.remove("hidden");
        modal.classList.add("flex");
    };

    window.closeMethodsInfoModal = function () {
        const modal = document.getElementById("methods-info-modal");
        if (!modal) return;
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    };

// МОДАЛКА ДЛЯ ОТОБРАЖАНЕИЯ ДОГОВОРА ОБ ОКАЗАНИИ УСЛУГ
    window.openServiceAgreementModal = function (psychologistId) {
        const psychologists = getPsychologists();
        const ps = psychologists.find(item => item.id === psychologistId);
        if (!ps) return;

        const modal = document.getElementById("service-agreement-modal");
        const content = document.getElementById("service-agreement-content");
        if (!modal || !content) return;

        content.innerHTML = `
            <p>
                <strong>${ps.full_name}</strong> (далее — «Психолог») разместил настоящий текст,
                являющийся публичной офертой, т.е. предложением Психолога, указанного на соответствующей
                странице сайта и в мобильных приложениях, заключить договор с любым пользователем
                (далее — «Пользователь») относительно проведения психологических консультаций онлайн.
            </p>
            <p>
                В соответствии с пунктом 3 статьи 438 Гражданского кодекса Российской Федерации
                надлежащим акцептом настоящей оферты считается последовательное осуществление Пользователем
                следующих действий:
            </p>
            <ul class="list-disc pl-5 space-y-2">
                <li>ознакомление с условиями настоящей оферты;</li>
                <li>введение регистрационных данных;</li>
                <li>нажатие кнопки «Оплатить» или аналога.</li>
            </ul>
            <p class="pt-4">
                С момента совершения указанных действий договор оказания услуг считается заключённым
                между Психологом и Пользователем.
            </p>
        `;

        modal.classList.remove("hidden");
        modal.classList.add("flex");
    };

    window.closeServiceAgreementModal = function () {
        const modal = document.getElementById("service-agreement-modal");
        if (!modal) return;
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    };
}
