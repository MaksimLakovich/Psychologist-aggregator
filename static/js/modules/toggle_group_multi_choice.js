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
    initialValues = [],
    maxSelected = null,
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

    // 1) Вспомогательная функция: переводит одну конкретную кнопку в неактивное состояние.
    // Простыми словами:
    // - убираем у кнопки оформление "выбрано";
    // - возвращаем ей обычный внешний вид, который означает "эта опция сейчас не выбрана".
    function setInactive(btn) {
        removeClasses(btn, ACTIVE_CLASSES);
        addClasses(btn, INACTIVE_CLASSES);
    }

    // 2) Вспомогательная функция: переводит одну конкретную кнопку в активное состояние.
    // Простыми словами:
    // - визуально подсвечиваем кнопку;
    // - показываем пользователю, что именно эта опция сейчас выбрана.
    function setActive(btn) {
        addClasses(btn, ACTIVE_CLASSES);
        removeClasses(btn, INACTIVE_CLASSES);
    }

    function toggleBtn(btn) {
        const isActive = ACTIVE_CLASSES.every(c => btn.classList.contains(c));

        if (isActive) {
            setInactive(btn);
        } else {
            // Режим maxSelected=1 нужен для сценария "выбрать 1 или снять выбор совсем".
            // Пример такого сценария:
            // - страница "Каталог" -> фильтр "Вид консультации";
            // - пользователь может выбрать только "Индивидуальная" ИЛИ только "Парная";
            // - при повторном клике по активной кнопке можно снять выбор полностью и вернуться к состоянию "все".
            //
            // Если maxSelected не задан:
            // - остается прежний сценарий работы модуля, который используется на странице personal-questions/;
            // - можно выбирать несколько кнопок одновременно без автоматического снятия других значений.
            if (maxSelected === 1) {
                buttons.forEach(otherBtn => {
                    if (otherBtn !== btn) {
                        setInactive(otherBtn);
                    }
                });
            }

            setActive(btn);
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
            setActive(btn);
        }
    });

    // Это защитная логика на случай некорректного стартового состояния.
    // Например:
    // - режим maxSelected=1 говорит, что активной может быть только ОДНА кнопка;
    // - но если по ошибке в initialValues пришло сразу 2 значения
    //   (например, ["individual", "couple"]),
    //   то UI не должен показать пользователю две активные кнопки одновременно.
    //
    // Что делаем:
    // - оставляем активной только первую найденную кнопку;
    // - все остальные принудительно переводим в неактивное состояние.
    //
    // То есть простыми словами:
    // если входные данные противоречат правилу "можно выбрать только один вариант",
    // модуль сам мягко исправляет это состояние.
    if (maxSelected === 1) {
        let wasFirstSelectedFound = false;
        buttons.forEach(btn => {
            const isActive = ACTIVE_CLASSES.every(c => btn.classList.contains(c));
            if (!isActive) return;

            if (!wasFirstSelectedFound) {
                wasFirstSelectedFound = true;
                return;
            }

            setInactive(btn);
        });
    }

    // Назначаем обработчики
    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            toggleBtn(btn);
        });
    });

    // Синхронизируем скрытые input'ы с начальными значениями
    syncHiddenInputs();
}
