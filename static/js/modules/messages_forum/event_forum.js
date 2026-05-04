import { pluralizeRu } from "../../utils/pluralize_ru.js";

// Этот модуль оживляет messages-блок на detail-странице события.
// 1. Здесь нет бизнес-логики доступа - backend уже решил, можно ли писать и редактировать сообщения.
// 2. JS отвечает только за UX:
//     - показать скрытые более ранние сообщения над текущей перепиской;
//     - развернуть длинный текст сообщения;
//     - открыть/закрыть inline-форму редактирования.

const thread = document.querySelector("[data-comments-thread]");
const messageCountBadge = document.querySelector("[data-message-count-badge]");
const commentsArticle = document.querySelector("#session-comments");
const commentsScrollTargetKey = "therapySessionCommentsScrollTarget";

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

  function getVisibleComments() {
    return commentNodes.filter((commentNode) => !commentNode.classList.contains("hidden"));
  }

  function getHiddenComments() {
    return commentNodes.filter((commentNode) => commentNode.classList.contains("hidden"));
  }

  function collapseCommentsToInitialChunk() {
    const firstVisibleIndex = Math.max(commentNodes.length - visibleCommentsLimit, 0);

    commentNodes.forEach((commentNode, commentIndex) => {
      const shouldStayVisible = commentIndex >= firstVisibleIndex;

      commentNode.classList.toggle("hidden", !shouldStayVisible);
    });
  }

  function revealCommentFromHistory(commentNode) {
    const commentIndex = commentNodes.indexOf(commentNode);
    const firstVisibleIndex = commentNodes.findIndex((node) => !node.classList.contains("hidden"));

    if (commentIndex < 0 || firstVisibleIndex < 0 || commentIndex >= firstVisibleIndex) {
      commentNode.classList.remove("hidden");
      return;
    }

    commentNodes.slice(commentIndex, firstVisibleIndex).forEach((node) => {
      node.classList.remove("hidden");
    });
  }

  function syncShowMoreButtonLabel() {
    if (!showMoreButton) {
      return;
    }

    const hiddenCommentsCount = getHiddenComments().length;
    if (hiddenCommentsCount <= 0) {
      showMoreButton.textContent = "Скрыть";
      return;
    }

    const nextChunkCount = Math.min(hiddenCommentsCount, visibleCommentsLimit);
    showMoreButton.textContent =
      `Показать еще ${nextChunkCount} ${pluralizeRu(nextChunkCount, "сообщение", "сообщения", "сообщений")}`;
  }

  if (showMoreButton) {
    syncShowMoreButtonLabel();

    showMoreButton.addEventListener("click", () => {
      const hiddenComments = getHiddenComments();
      if (hiddenComments.length <= 0) {
        const buttonTopBeforeCollapse = showMoreButton.getBoundingClientRect().top;
        collapseCommentsToInitialChunk();

        requestAnimationFrame(() => {
          const buttonTopAfterCollapse = showMoreButton.getBoundingClientRect().top;
          window.scrollBy({
            top: buttonTopAfterCollapse - buttonTopBeforeCollapse,
            left: 0,
            behavior: "auto",
          });
          syncShowMoreButtonLabel();
        });
        return;
      }

      // В качестве якоря берем первое видимое сообщение.
      // Когда пользователь раскрывает более раннюю историю сверху,
      // это сообщение остается на той же позиции экрана и переписка не прыгает.
      const visibleComments = getVisibleComments();
      const anchorComment = visibleComments[0];
      const anchorTopBeforeExpand = anchorComment
        ? anchorComment.getBoundingClientRect().top
        : null;

      hiddenComments.slice(-visibleCommentsLimit).forEach((commentNode) => {
        commentNode.classList.remove("hidden");
      });

      requestAnimationFrame(() => {
        if (anchorComment && anchorTopBeforeExpand !== null) {
          const anchorTopAfterExpand = anchorComment.getBoundingClientRect().top;
          window.scrollBy({
            top: anchorTopAfterExpand - anchorTopBeforeExpand,
            left: 0,
            behavior: "auto",
          });
        }

        syncShowMoreButtonLabel();
      });
    });
  }

  if (commentsArticle) {
    commentsArticle.querySelectorAll("form").forEach((form) => {
      form.addEventListener("submit", () => {
        const formData = new FormData(form);
        const action = formData.get("action") || "add_message";
        const messageId = formData.get("message_id") || "";

        sessionStorage.setItem(
          commentsScrollTargetKey,
          JSON.stringify({
            action,
            messageId,
          }),
        );
      });
    });

    const savedTarget = sessionStorage.getItem(commentsScrollTargetKey);
    if (savedTarget) {
      sessionStorage.removeItem(commentsScrollTargetKey);

      try {
        const targetData = JSON.parse(savedTarget);
        const visibleComments = getVisibleComments();
        const targetComment = targetData.action === "edit_message"
          ? commentNodes.find((commentNode) => commentNode.dataset.commentId === targetData.messageId)
          : visibleComments[visibleComments.length - 1];

        if (targetComment) {
          revealCommentFromHistory(targetComment);
          syncShowMoreButtonLabel();

          requestAnimationFrame(() => {
            targetComment.scrollIntoView({
              block: "center",
              behavior: "auto",
            });
          });
        }
      } catch {
        commentsArticle.scrollIntoView({
          block: "start",
          behavior: "auto",
        });
      }
    }
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
