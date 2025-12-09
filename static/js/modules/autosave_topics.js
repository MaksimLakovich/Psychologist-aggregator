function debounce(fn, wait = 500) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
    };
}

export function initAutosaveTopics({ checkboxSelector, saveUrl, csrfToken, debounceMs = 500 }) {
    if (!saveUrl) {
        console.warn("initAutosaveTopics: saveUrl is required");
        return;
    }
    const checkboxes = Array.from(document.querySelectorAll(checkboxSelector));
    if (!checkboxes.length) return;

    const doSave = () => {
        const params = new URLSearchParams();
        checkboxes.forEach(cb => {
            if (cb.checked) params.append("topics[]", cb.value);
        });

        return fetch(saveUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": csrfToken || "",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            body: params.toString(),
        })
        .then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        })
        .then(data => {
            // TODO: вместо console.log - показать маленький UI-тултип/иконку "Сохранено"
            console.log("Автосохранение:", data);
        })
        .catch(err => {
            // TODO: показать пользователю notification об ошибке (UI-ошибка "Не удалось сохранить")
            console.error("Ошибка автосохранения:", err);
        });
    };

    const debouncedSave = debounce(doSave, debounceMs);

    checkboxes.forEach(cb => cb.addEventListener("change", debouncedSave));
}
