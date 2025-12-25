//-------------------------------------------------------------
// Общие классы (точно такие же как в toggle_group_single_choice.js)
//-------------------------------------------------------------
const ACTIVE_CLASSES = [
    "bg-indigo-500",
    "text-white",
    "border-indigo-100",
    "hover:bg-indigo-900"
];

const INACTIVE_CLASSES = [
    "bg-white",
    "text-gray-700",
    "border-gray-300",
    "hover:bg-gray-50"
];

function addClasses(el, classes) {
    classes.forEach(c => el.classList.add(c));
}

function removeClasses(el, classes) {
    classes.forEach(c => el.classList.remove(c));
}

//-------------------------------------------------------------
// MULTI-TOGGLE
//-------------------------------------------------------------
export function initMultiToggle({
    containerSelector,
    buttonSelector,
    hiddenInputsContainerSelector,
    inputName,
    initialValues = []
}) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const buttons = Array.from(container.querySelectorAll(buttonSelector));
    const hiddenWrap = document.querySelector(hiddenInputsContainerSelector);

    function syncHiddenInputs() {
        hiddenWrap.innerHTML = "";

        buttons.forEach(btn => {
            const isActive = ACTIVE_CLASSES.every(c => btn.classList.contains(c));
            if (isActive) {
                const input = document.createElement("input");
                input.type = "hidden";
                input.name = inputName;
                input.value = btn.dataset.value;
                hiddenWrap.appendChild(input);
            }
        });
    }

    function toggleBtn(btn) {
        const isActive = ACTIVE_CLASSES.every(c => btn.classList.contains(c));

        if (isActive) {
            removeClasses(btn, ACTIVE_CLASSES);
            addClasses(btn, INACTIVE_CLASSES);
        } else {
            addClasses(btn, ACTIVE_CLASSES);
            removeClasses(btn, INACTIVE_CLASSES);
        }

        syncHiddenInputs();
    }

    // Сначала: делаем все кнопки неактивными
    buttons.forEach(btn => {
        removeClasses(btn, ACTIVE_CLASSES);
        addClasses(btn, INACTIVE_CLASSES);
    });

    // Затем: восстанавливаем состояние из initialValues
    buttons.forEach(btn => {
        if (initialValues.includes(btn.dataset.value)) {
            addClasses(btn, ACTIVE_CLASSES);
            removeClasses(btn, INACTIVE_CLASSES);
        }
    });

    // Назначаем обработчики
    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            toggleBtn(btn);
        });
    });

    // Синхронизируем скрытые input'ы с начальными значениями
    syncHiddenInputs();
}
