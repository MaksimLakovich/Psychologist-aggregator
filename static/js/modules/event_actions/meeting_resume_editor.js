/**
 * Inline-редактор итогов встречи на detail-странице терапевтической сессии.
 *
 * Бизнес-смысл:
 * - специалист видит уже сохраненные итоги как обычный текст;
 * - поле редактирования открывается только по явному действию;
 * - в режиме редактирования текст не дублируется рядом с textarea.
 */

function initMeetingResumeEditor() {
    document.querySelectorAll("[data-meeting-resume-editor]").forEach((editorElement) => {
        const viewElement = editorElement.querySelector("[data-meeting-resume-view]");
        const formElement = editorElement.querySelector("[data-meeting-resume-form]");
        const openButton = editorElement.querySelector("[data-meeting-resume-open]");
        const cancelButton = editorElement.querySelector("[data-meeting-resume-cancel]");
        const resumeTextarea = editorElement.querySelector("textarea[name='meeting_resume']");

        if (!viewElement || !formElement || !openButton || !cancelButton) {
            return;
        }

        openButton.addEventListener("click", () => {
            viewElement.classList.add("hidden");
            openButton.style.display = "none";
            formElement.classList.remove("hidden");

            if (resumeTextarea) {
                resumeTextarea.focus();
            }
        });

        cancelButton.addEventListener("click", () => {
            if (resumeTextarea) {
                resumeTextarea.value = resumeTextarea.defaultValue;
            }

            formElement.classList.add("hidden");
            viewElement.classList.remove("hidden");
            openButton.style.display = "";
        });
    });
}

document.addEventListener("DOMContentLoaded", initMeetingResumeEditor);
