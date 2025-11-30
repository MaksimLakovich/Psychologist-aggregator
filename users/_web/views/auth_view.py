# import os

from django.contrib.auth import login
# from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
# from django.core.mail import send_mail
from django.urls import reverse_lazy
# from django.views.generic import UpdateView
# from django.views.generic.edit import FormView
# from dotenv import load_dotenv

from users._web.forms.auth_form import AppUserLoginForm
# from users.models import UserCustomer

# # Загрузка переменных из .env-файла
# load_dotenv()


class AppUserLoginView(LoginView):
    """Класс-контроллер на основе auth.views для входа ранее зарегистрированного пользователя в систему."""

    # Явно указываю кастомную форму для входа пользователя, без этого у меня почему-то не подтягиваются определенные в
    # форме AppUserLoginForm стили (наверное, потому что по умолчанию LoginView использует стандартную
    # форму Django → AuthenticationForm.)
    authentication_form = AppUserLoginForm
    template_name = "users/login_page.html"
    success_url = reverse_lazy("core:home_page")

    # def get_success_url(self):
    #     """Явно указываю редирект переопределяя метод, так как обычный вариант в виде "success_url = reverse_lazy()"
    #     не работал. Django его игнорировал и отправлял на /accounts/profile/"""
    #     return reverse_lazy("core:home_page")

    def form_valid(self, form):
        """Автоматический вход пользователя после успешной аутентификации."""
        login(self.request, form.get_user())
        return super().form_valid(form)


# class CustomRegisterView(FormView):
#     """Представление для отображения страницы регистрации нового пользователя (register.html)."""
#
#     form_class = UserCustomerRegistrationForm
#     template_name = "users/register.html"
#     success_url = reverse_lazy("catalog:home_page")  # Редирект после регистрации
#
#     def form_valid(self, form):
#         """Сохранение нового пользователя и автоматический вход после регистрации."""
#         user = form.save()
#         login(self.request, user)
#         self.send_welcome_email(
#             user
#         )  # Запрос на отправку приветственного письма после регистрации
#         return super().form_valid(form)
#
#     def send_welcome_email(self, user):
#         """Отправка приветственного письма пользователю после успешной регистрации."""
#         subject = "Регистрация в магазине Skystore!"
#         message = (
#             f"Спасибо, что зарегистрировались в нашем магазине!\n\n"
#             f"Почта для входа: {user.email}\n\n"
#             f"После регистрации в интернет-магазине Skystore Вы можете публиковать свои плагины и"
#             f"примеры кода для поиска покупателей."
#         )
#         from_email = os.getenv("YANDEX_EMAIL_HOST_USER")
#         if not from_email:
#             raise ValueError(
#                 "Переменная окружения YANDEX_EMAIL_HOST_USER не загружена!"
#             )
#         recipient_list = [user.email]
#         send_mail(
#             subject=subject,
#             message=message,
#             from_email=from_email,
#             recipient_list=recipient_list,
#             fail_silently=False,
#         )
#
#
# class CustomEditProfileView(LoginRequiredMixin, UpdateView):
#     """Представление для редактирования профиля зарегистрированного пользователя (user_profile_edit.html)."""
#
#     model = UserCustomer
#     form_class = UserProfileEditForm
#     template_name = "users/user_profile_edit.html"
#     success_url = reverse_lazy("catalog:home_page")  # Редирект после изменения данных
#
#     def get_object(self, queryset=None):
#         """Возвращаем текущего пользователя, чтобы редактировать только свой профиль."""
#         return self.request.user
#
#     def form_valid(self, form):
#         """Сохранение изменений профиля пользователя и запрос отправки уведомления на почту."""
#         # Этот вариант более чистый / профессиональны по сравнению с тем, как я реализовывал раньше в
#         # CustomRegisterView для "send_welcome_email"
#         # 1) Django сам вызывает form.save() поэтому та строка по сути лишняя
#         # 2) "self.object" - это уже и есть сохраненный пользователь (т.е. user)
#         response = super().form_valid(form)
#         self.send_info_email(self.object)
#         return response
#
#     def send_info_email(self, user):
#         """Отправка письма пользователю после успешного изменения данных в его профиле."""
#
#         subject = "Изменение данных пользователя в магазине Skystore!"
#         message = "Ваши данные были изменены."
#
#         from_email = os.getenv("YANDEX_EMAIL_HOST_USER")
#         if not from_email:
#             raise ValueError(
#                 "Переменная окружения YANDEX_EMAIL_HOST_USER не загружена!"
#             )
#         recipient_list = [user.email]
#         send_mail(
#             subject=subject,
#             message=message,
#             from_email=from_email,
#             recipient_list=recipient_list,
#             fail_silently=False,
#         )
#
#
# class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
#     """Представление для изменения пароля пользователя (change_password.html)."""
#
#     form_class = UserPasswordChangeForm
#     template_name = "users/change_password.html"
#     success_url = reverse_lazy("catalog:home_page")  # Редирект после изменения пароля
