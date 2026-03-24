/**
 * Дополнительное UI-поведение страницы "Запланированные сессии".
 */


// Функция для того, чтоб после успешного бронирования при переводе его на страниц "Запланированные сессии":
// - система мягко подводит к только что созданной сессии, чтобы сразу увидел, что запись действительно появилась
function scrollToRecentlyCreatedSession() {
    const recentSessionElement = document.querySelector("[data-recently-created-session]");
    if (!recentSessionElement) {
        return;
    }

    window.setTimeout(() => {
        recentSessionElement.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    }, 250);
}

document.addEventListener("DOMContentLoaded", scrollToRecentlyCreatedSession);
