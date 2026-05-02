/**
 * Inline-редактор описания события на detail-странице терапевтической сессии.
 *
 * Бизнес-смысл:
 * - в обычном состоянии специалист видит описание как часть общей карточки встречи;
 * - при редактировании карточка не должна показывать один и тот же текст дважды;
 * - кнопка "Отменить" возвращает специалиста к просмотру без сохранения случайных правок.
 */

function initEventDescriptionEditor() {
    document.querySelectorAll("[data-event-description-editor]").forEach((editorElement) => {
        const viewElement = editorElement.querySelector("[data-event-description-view]");
        const formElement = editorElement.querySelector("[data-event-description-form]");
        const openButton = editorElement.querySelector("[data-event-description-open]");
        const cancelButton = editorElement.querySelector("[data-event-description-cancel]");
        const descriptionTextarea = editorElement.querySelector("textarea");

        if (!viewElement || !formElement || !openButton || !cancelButton) {
            return;
        }

        openButton.addEventListener("click", () => {
            viewElement.classList.add("hidden");
            openButton.style.display = "none";
            formElement.classList.remove("hidden");

            if (descriptionTextarea) {
                descriptionTextarea.focus();
            }
        });

        cancelButton.addEventListener("click", () => {
            if (descriptionTextarea) {
                descriptionTextarea.value = descriptionTextarea.defaultValue;
            }

            formElement.classList.add("hidden");
            viewElement.classList.remove("hidden");
            openButton.style.display = "";
        });
    });
}

document.addEventListener("DOMContentLoaded", initEventDescriptionEditor);
