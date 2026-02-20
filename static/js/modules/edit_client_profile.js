/**
 * Скрипт управляет режимами просмотра/редактирования формы профиля клиента.
 * Логика простая:
 * 1) При загрузке страницы ставим поля в "режим просмотра" (readonly/disabled).
 * 2) При нажатии "Редактировать" включаем редактирование и показываем кнопки "Сохранить/Отмена".
 * 3) При нажатии "Отмена" возвращаем исходные значения формы и снова блокируем поля.
 */

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("profile-edit-form");
  if (!form) return;

  const toggleBtn = document.getElementById("profile-edit-toggle");
  const cancelBtn = document.getElementById("profile-edit-cancel");
  const editActions = document.getElementById("profile-edit-actions");
  const displayActions = document.getElementById("display-actions");

  // Все поля, которые можно редактировать (email исключаем)
  const inputs = form.querySelectorAll('input:not([name="email"]), select');

  /**
   * Переключает форму между режимом просмотра и редактирования.
   * @param {boolean} isEditing - true, если включаем редактирование.
   */
  function setEditMode(isEditing) {
    inputs.forEach((input) => {
      if (isEditing) {
        input.removeAttribute("readonly");
        input.disabled = false;
      } else {
        if (input.tagName !== "SELECT") {
          input.setAttribute("readonly", "readonly");
        }
        if (input.tagName === "SELECT") {
          input.disabled = true;
        }
      }
    });

    if (isEditing) {
      editActions.classList.remove("hidden");
      displayActions.classList.add("hidden");
    } else {
      editActions.classList.add("hidden");
      displayActions.classList.remove("hidden");
    }
  }

  // Инициализация: показываем режим просмотра
  setEditMode(false);

  // Кнопка "Редактировать"
  toggleBtn.addEventListener("click", function () {
    setEditMode(true);
  });

  // Кнопка "Отмена"
  cancelBtn.addEventListener("click", function () {
    form.reset();
    setEditMode(false);
  });
});
