/**
 * UI-поведение страницы "Запланированные сессии".
 */

// Функция для автоматического скрытия системного уведомления "Сессия успешно записана!", должно мягко исчезать само,
// чтобы не занимать место на странице после того, как клиент уже увидел подтверждение;
// - исчезновение должно быть двухфазным:
//   1) сначала карточка плавно теряет акцент и визуально "затухает";
//   2) затем аккуратно схлопывается и освобождает место в потоке страницы.
function initAutoDismissMessages() {
    document.querySelectorAll("[data-auto-dismiss-message]").forEach((element) => {
        window.setTimeout(() => {
            element.classList.add("is-fading");

            window.setTimeout(() => {
                element.classList.add("is-collapsing");

                window.setTimeout(() => {
                    element.remove();
                }, 700);
            }, 450);
        }, 3500);
    });
}

document.addEventListener("DOMContentLoaded", initAutoDismissMessages);
