/**
 * Inline-редактор ссылки на видеовстречу в блоке "Подключение".
 *
 * Бизнес-смысл:
 * - специалист сначала видит понятное состояние подключения без пустого поля ввода;
 * - добавление и редактирование ссылки открывает поле только по явному действию;
 * - отмена возвращает специалиста к прежнему виду блока без сохранения случайных правок.
 */

function initMeetingUrlEditor() {
    document.querySelectorAll("[data-meeting-url-editor]").forEach((editorElement) => {
        const viewElement = editorElement.querySelector("[data-meeting-url-view]");
        const formElement = editorElement.querySelector("[data-meeting-url-form]");
        const openButton = editorElement.querySelector("[data-meeting-url-open]");
        const cancelButton = editorElement.querySelector("[data-meeting-url-cancel]");
        const meetingUrlInput = editorElement.querySelector("input[name='meeting_url']");

        if (!viewElement || !formElement || !openButton || !cancelButton) {
            return;
        }

        openButton.addEventListener("click", () => {
            viewElement.classList.add("hidden");
            openButton.style.display = "none";
            formElement.classList.remove("hidden");

            if (meetingUrlInput) {
                meetingUrlInput.focus();
            }
        });

        cancelButton.addEventListener("click", () => {
            if (meetingUrlInput) {
                meetingUrlInput.value = meetingUrlInput.defaultValue;
            }

            formElement.classList.add("hidden");
            viewElement.classList.remove("hidden");
            openButton.style.display = "";
        });
    });
}

document.addEventListener("DOMContentLoaded", initMeetingUrlEditor);
