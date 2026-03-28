// Этот модуль оживляет messages-блок на detail-странице события.
// 1. Здесь нет бизнес-логики доступа - backend уже решил, можно ли писать и редактировать сообщения.
// 2. JS отвечает только за UX:
//     - показать скрытые старые сообщения;
//     - развернуть длинный текст сообщения;
//     - открыть/закрыть inline-форму редактирования.

const thread = document.querySelector("[data-comments-thread]");

if (thread) {
  const showMoreButton = thread.querySelector("[data-show-more-comments]");
  if (showMoreButton) {
    showMoreButton.addEventListener("click", () => {
      thread.querySelectorAll("[data-comment-hidden]").forEach((commentNode) => {
        commentNode.classList.remove("hidden");
      });
      showMoreButton.remove();
    });
  }

  thread.querySelectorAll("[data-toggle-message-full]").forEach((toggleButton) => {
    toggleButton.addEventListener("click", () => {
      const messageContainer = toggleButton.closest("[data-comment-display-body]");
      if (!messageContainer) {
        return;
      }

      const previewNode = messageContainer.querySelector("[data-message-preview]");
      const fullNode = messageContainer.querySelector("[data-message-full]");
      if (!previewNode || !fullNode) {
        return;
      }

      const isExpanded = !fullNode.classList.contains("hidden");
      if (isExpanded) {
        fullNode.classList.add("hidden");
        previewNode.classList.remove("hidden");
        toggleButton.textContent = "Развернуть";
      } else {
        previewNode.classList.add("hidden");
        fullNode.classList.remove("hidden");
        toggleButton.textContent = "Свернуть";
      }
    });
  });

  thread.querySelectorAll("[data-comment-edit-toggle]").forEach((toggleButton) => {
    toggleButton.addEventListener("click", () => {
      const commentWrapper = toggleButton.closest(".w-full");
      if (!commentWrapper) {
        return;
      }

      const editForm = commentWrapper.querySelector("[data-comment-edit-form]");
      if (!editForm) {
        return;
      }

      editForm.classList.toggle("hidden");
    });
  });

  thread.querySelectorAll("[data-comment-edit-cancel]").forEach((cancelButton) => {
    cancelButton.addEventListener("click", () => {
      const editForm = cancelButton.closest("[data-comment-edit-form]");
      if (!editForm) {
        return;
      }

      editForm.classList.add("hidden");
    });
  });
}
