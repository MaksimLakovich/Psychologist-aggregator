import { pluralizeRu } from "../../utils/pluralize_ru.js";

// Этот модуль оживляет messages-блок на detail-странице события.
// 1. Здесь нет бизнес-логики доступа - backend уже решил, можно ли писать и редактировать сообщения.
// 2. JS отвечает только за UX:
//     - показать скрытые старые сообщения;
//     - развернуть длинный текст сообщения;
//     - открыть/закрыть inline-форму редактирования.

const thread = document.querySelector("[data-comments-thread]");
const messageCountBadge = document.querySelector("[data-message-count-badge]");

function buildMessagesCountLabel(count) {
  return `${count} ${pluralizeRu(count, "сообщение", "сообщения", "сообщений")}`;
}

if (messageCountBadge) {
  const messageCount = Number(messageCountBadge.dataset.messageCount || 0);
  messageCountBadge.textContent = buildMessagesCountLabel(messageCount);
}

if (thread) {
  const commentNodes = Array.from(thread.querySelectorAll("[data-comment-item]"));
  const visibleCommentsLimit = Number(thread.dataset.visibleCommentsLimit || 10);
  const showMoreButton = thread.querySelector("[data-show-more-comments]");

  function syncCommentsVisibility(isExpanded) {
    commentNodes.forEach((commentNode) => {
      const commentIndex = Number(commentNode.dataset.commentIndex || 0);
      const shouldStayVisible = isExpanded || commentIndex <= visibleCommentsLimit;

      commentNode.classList.toggle("hidden", !shouldStayVisible);
    });
  }

  function syncShowMoreButtonLabel(isExpanded) {
    if (!showMoreButton) {
      return;
    }

    const hiddenCommentsCount = Number(showMoreButton.dataset.showMoreCount || 0);
    showMoreButton.textContent = isExpanded
      ? "Скрыть"
      : `Показать еще ${hiddenCommentsCount} ${pluralizeRu(hiddenCommentsCount, "сообщение", "сообщения", "сообщений")}`;
  }

  if (showMoreButton) {
    let isExpanded = false;
    syncShowMoreButtonLabel(isExpanded);

    showMoreButton.addEventListener("click", () => {
      isExpanded = !isExpanded;
      syncCommentsVisibility(isExpanded);
      syncShowMoreButtonLabel(isExpanded);
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
        toggleButton.textContent = "Показать все";
      } else {
        previewNode.classList.add("hidden");
        fullNode.classList.remove("hidden");
        toggleButton.textContent = "Скрыть";
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
