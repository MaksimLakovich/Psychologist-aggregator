/*
 * Управляет модалками тем и подходов:
 * открывает окна, возвращает несохраненный выбор назад и отправляет сохранение на сервер.
 */
document.addEventListener("DOMContentLoaded", () => {
    const modalConfigs = {
        "topics-modal": {
            modalId: "topics-modal",
            saveButtonId: "save-topics-button",
            errorId: "topics-modal-error",
            checkboxSelector: ".topic-checkbox",
            fieldName: "topics[]",
            containerId: "selected-topics-container",
            badgeClassName: "selection-badge topic-badge",
            emptyText: "Темы пока не выбраны",
        },
        "methods-modal": {
            modalId: "methods-modal",
            saveButtonId: "save-methods-button",
            errorId: "methods-modal-error",
            checkboxSelector: ".method-checkbox",
            fieldName: "methods[]",
            containerId: "selected-methods-container",
            badgeClassName: "selection-badge method-badge",
            emptyText: "Подходы пока не выбраны",
        },
    }
    const modalState = new Map()
    const openButtons = document.querySelectorAll("[data-modal-open]")
    const modals = document.querySelectorAll("[data-modal]")

    /* Возвращает массив выбранных значений из чекбоксов конкретной модалки. */
    function readCheckedValues(checkboxSelector) {
        return Array.from(document.querySelectorAll(`${checkboxSelector}:checked`)).map((checkbox) => checkbox.value)
    }

    /* Возвращает все чекбоксы нужной модалки для дальнейшей синхронизации выбора. */
    function getCheckboxes(checkboxSelector) {
        return Array.from(document.querySelectorAll(checkboxSelector))
    }

    /* Восстанавливает чекбоксы в то состояние, которое сейчас сохранено в базе. */
    function applyCheckedValues(checkboxSelector, values) {
        const valuesSet = new Set(values)

        getCheckboxes(checkboxSelector).forEach((checkbox) => {
            checkbox.checked = valuesSet.has(checkbox.value)
        })
    }

    /* Очищает текст ошибки, чтобы модалка открывалась в чистом состоянии. */
    function clearModalError(errorElement) {
        if (!errorElement) {
            return
        }

        errorElement.textContent = ""
        errorElement.classList.add("hidden")
    }

    /* Показывает ошибку сохранения прямо внутри открытой модалки. */
    function showModalError(errorElement, message) {
        if (!errorElement) {
            return
        }

        errorElement.textContent = message
        errorElement.classList.remove("hidden")
    }

    /* Блокирует прокрутку страницы только пока хотя бы одна модалка реально открыта. */
    function syncBodyScrollLock() {
        const hasOpenedModal = Array.from(modals).some((modal) => !modal.classList.contains("hidden"))
        document.body.classList.toggle("overflow-hidden", hasOpenedModal)
    }

    /* Перерисовывает бейджи на карточке после успешного сохранения на сервере. */
    function renderBadges(containerId, labels, badgeClassName, emptyText) {
        const container = document.getElementById(containerId)
        if (!container) {
            return
        }

        container.innerHTML = ""

        if (!labels.length) {
            const emptyState = document.createElement("span")
            emptyState.className = "text-sm text-zinc-500"
            emptyState.textContent = emptyText
            container.appendChild(emptyState)
            return
        }

        labels.forEach((label) => {
            const badge = document.createElement("span")
            badge.className = badgeClassName
            badge.textContent = label
            container.appendChild(badge)
        })
    }

    /* Возвращает настройки модалки по ее id, чтобы не дублировать логику. */
    function getModalConfigById(modalId) {
        return modalConfigs[modalId] || null
    }

    /* Открывает модалку и подставляет только последнее сохраненное состояние выбора. */
    function openModal(modalId) {
        const modal = document.getElementById(modalId)
        const modalConfig = getModalConfigById(modalId)
        if (!modal || !modalConfig) {
            return
        }

        applyCheckedValues(modalConfig.checkboxSelector, modalState.get(modalId) || [])
        clearModalError(document.getElementById(modalConfig.errorId))
        modal.classList.remove("hidden")
        syncBodyScrollLock()
    }

    /* Закрывает модалку и при необходимости откатывает несохраненный выбор назад. */
    function closeModal(modalId, { restoreSavedState = true } = {}) {
        const modal = document.getElementById(modalId)
        const modalConfig = getModalConfigById(modalId)
        if (!modal || !modalConfig) {
            return
        }

        if (restoreSavedState) {
            applyCheckedValues(modalConfig.checkboxSelector, modalState.get(modalId) || [])
        }

        clearModalError(document.getElementById(modalConfig.errorId))
        modal.classList.add("hidden")
        syncBodyScrollLock()
    }

    /* Собирает подписи выбранных пунктов для обновления бейджей на странице. */
    function collectSelectedLabels(checkboxSelector) {
        return Array.from(document.querySelectorAll(`${checkboxSelector}:checked`))
            .map((checkbox) => checkbox.dataset.label || "")
            .filter(Boolean)
    }

    /* Отправляет новый выбор на сервер и фиксирует его как сохраненное состояние. */
    async function saveSelection(modalId) {
        const modalConfig = getModalConfigById(modalId)
        if (!modalConfig) {
            return
        }

        const saveButton = document.getElementById(modalConfig.saveButtonId)
        const errorElement = document.getElementById(modalConfig.errorId)
        if (!saveButton) {
            return
        }

        const formData = new FormData()
        const selectedValues = readCheckedValues(modalConfig.checkboxSelector)

        clearModalError(errorElement)
        selectedValues.forEach((value) => {
            formData.append(modalConfig.fieldName, value)
        })

        const originalLabel = saveButton.textContent
        saveButton.disabled = true
        saveButton.textContent = "Сохраняем..."

        try {
            const response = await fetch(saveButton.dataset.saveUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": saveButton.dataset.csrfToken,
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: formData,
            })

            if (!response.ok) {
                throw new Error("Не удалось сохранить изменения. Попробуйте еще раз.")
            }

            modalState.set(modalId, selectedValues)
            renderBadges(
                modalConfig.containerId,
                collectSelectedLabels(modalConfig.checkboxSelector),
                modalConfig.badgeClassName,
                modalConfig.emptyText,
            )
            closeModal(modalId, { restoreSavedState: false })
        } catch (error) {
            showModalError(errorElement, error.message)
        } finally {
            saveButton.disabled = false
            saveButton.textContent = originalLabel
        }
    }

    Object.values(modalConfigs).forEach((modalConfig) => {
        modalState.set(modalConfig.modalId, readCheckedValues(modalConfig.checkboxSelector))
    })

    openButtons.forEach((button) => {
        button.addEventListener("click", () => {
            openModal(button.dataset.modalOpen)
        })
    })

    modals.forEach((modal) => {
        modal.querySelectorAll("[data-modal-close]").forEach((button) => {
            button.addEventListener("click", () => {
                closeModal(modal.id)
            })
        })

        modal.addEventListener("click", (event) => {
            if (event.target === modal) {
                closeModal(modal.id)
            }
        })
    })

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return
        }

        const openedModal = Array.from(modals).find((modal) => !modal.classList.contains("hidden"))
        if (openedModal) {
            closeModal(openedModal.id)
        }
    })

    document.getElementById("save-topics-button")?.addEventListener("click", () => {
        saveSelection("topics-modal")
    })

    document.getElementById("save-methods-button")?.addEventListener("click", () => {
        saveSelection("methods-modal")
    })
})
