from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from calendar_engine.booking.exceptions import \
    CreateTherapySessionValidationError
from calendar_engine.booking.use_cases.therapy_session_create import \
    CreateTherapySessionUseCase
from core.forms.client.specialist_matching.form_payment_card import \
    ClientAddPaymentCardForm
from core.services.anonymous_client_flow_for_search_and_booking import (
    get_guest_pending_booking, set_guest_pending_booking)
from core.services.get_client_timezone_value import \
    get_client_timezone_value_for_request
from core.services.mixins_current_layout import SpecialistMatchingLayoutMixin


class ClientAddPaymentCardPageView(SpecialistMatchingLayoutMixin, FormView):
    """Контроллер на основе FormView для отображения страницы *Завершение записи и добавление платежной карты*.

    Вью работает в двух сценариях:
        - сценарий 1: работает зарегистрированный авторизованный пользователь;
        - сценарий 2: работает guest-anonymous.
    """

    template_name = "core/client_pages/specialist_matching/home_client_payment_card.html"
    form_class = ClientAddPaymentCardForm

    def get_success_url(self):
        """Формирует URL следующего шага с сохранением текущего layout."""
        return f"{reverse('core:client-planned-sessions')}{self._build_layout_query()}"

    def get_initial(self):
        """Подтягивает на страницу подтверждения те данные, которые клиент уже выбрал на предыдущем шаге
        для двух сценариев.

        Бизнес-смысл:
            - на странице payment-card клиент уже не выбирает специалиста и время заново, а только подтверждает запись;
            - поэтому сервер берет из URL этого шага уже выбранные значения:
                - какого специалиста выбрали;
                - какой слот выбрали;
                - какой формат сессии выбрали;
            - после этого эти значения попадают в скрытые поля формы и используются для финального подтверждения.
        """
        initial = super().get_initial()

        # get_guest_pending_booking() - возвращает отложенное бронирование guest-anonymous, если оно есть
        fallback_booking = get_guest_pending_booking(self.request.session)

        # Тут обрабатывается 2 сценария:
        initial.update(
            {
                "specialist_profile_id": self.request.GET.get(
                    "specialist_profile_id",
                    (fallback_booking or {}).get("specialist_profile_id", ""),
                ),
                "slot_start_iso": self.request.GET.get(
                    "slot_start_iso",
                    (fallback_booking or {}).get("slot_start_iso", ""),
                ),
                "consultation_type": self.request.GET.get(
                    "consultation_type",
                    (fallback_booking or {}).get("consultation_type", ""),
                ),
            }
        )
        return initial

    def form_valid(self, form):
        """Создает терапевтическую сессию после подтверждения на странице payment-card для двух сценариев.

        Бизнес-смысл текущего этапа:
            - реальной оплаты и сохранения карты пока нет;
            - кнопка "Добавить карту и записаться" моделирует успешное завершение этого шага;
            - для сценария 1: после submit сразу создается терапевтическая сессия и клиент получает подтверждение;
            - для сценария 2: после submit бронь записывается в session и ставится на паузу до завершения регистрации.
        """
        # Сценарий 2: Guest-anonymous.
        # set_guest_pending_booking() - ставит бронирование guest-anonymous на паузу в session до регистрации
        if not self.request.user.is_authenticated:
            set_guest_pending_booking(
                self.request.session,
                specialist_profile_id=form.cleaned_data["specialist_profile_id"],
                slot_start_iso=form.cleaned_data["slot_start_iso"],
                consultation_type=form.cleaned_data["consultation_type"],
            )
            messages.info(
                self.request,
                "Чтобы завершить запись для выбранного специалиста и слота, войдите или зарегистрируйтесь.",
            )
            return redirect("users:web:login-page")

        # Сценарий 1: Авторизованный клиент. Сохраняем данные в реальные модели данных в БД
        use_case = CreateTherapySessionUseCase()

        try:
            booking_result = use_case.execute(
                client_user=self.request.user,
                specialist_profile_id=form.cleaned_data["specialist_profile_id"],
                slot_start_iso=form.cleaned_data["slot_start_iso"],
                consultation_type=form.cleaned_data["consultation_type"],
            )
        except CreateTherapySessionValidationError as exc:
            # Если backend не смог создать встречу, возвращаем клиента на эту же страницу
            # и показываем понятное сообщение прямо над формой.
            # Пример:
            #   - клиент открыл payment-card;
            #   - пока он нажимал кнопку, выбранный слот уже занял другой пользователь;
            #   - тогда вместо "тихой" ошибки мы показываем причину на текущем экране.
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        # Сохраняем id только что созданной встречи в session,
        # чтобы на следующей странице "Запланированные" можно было визуально подсветить именно эту новую запись.
        # Например:
        #   - клиент завершил запись на 11 марта 18:00;
        #   - после redirect список может содержать несколько будущих сессий;
        #   - по этому id экран понимает, какую из них отметить как "Только что создано".
        self.request.session["last_created_booking_id"] = str(booking_result["event"].id)

        messages.success(self.request, "Сессия успешно записана!")

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Формирование контекста для передачи данных в HTML-шаблон.
        1) Метод вызывается автоматически при рендеринге HTML-страницы и дополняет базовый контекст
        пользовательскими ключами, которые затем можно вывести в html-странице через Django Template Language.
        2) Возвращает:
            - dict: словарь со всеми данными, доступными внутри HTML-шаблона.
        """
        context = super().get_context_data(**kwargs)

        context["title_home_page_view"] = "Психологи онлайн на Опора — поиск и подбор психолога"

        # get_client_timezone_value_for_request() - возвращает TZ текущего участника flow в строковом виде:
        # - для авторизованного клиента timezone берется из аккаунта;
        # - для гостя из временного guest-anonymous-состояния в session, собранного на первом шаге подбора
        context["client_timezone_value"] = get_client_timezone_value_for_request(self.request)

        # Проверяем, все ли обязательные выборы из предыдущего шага действительно доехали до страницы подтверждения.
        # Если хотя бы одного значения нет, значит клиент пришел на payment-card "в обход" нормального сценария
        # и страница не должна считать набор данных готовым к финальному подтверждению записи.

        # all(...) - это встроенная функция, которая возвращает True только если каждое условие внутри выполнено
        context["booking_selection_ready"] = all(
            self.get_initial().get(field_name)  # Достаем значение этого поля из данных этой формы
            for field_name in ("specialist_profile_id", "slot_start_iso", "consultation_type")
        )

        # Логика управление отображением сайдбара:
        # 1) если пришли из сайдбара, показываем его;
        # 2) и показываем верхнее меню без сайдбара, если открыли не из сайдбара
        self._apply_layout_context(context)

        # Источник истины для серверной подсветки (route-based) текущего выбранного пункта в БОКОВОЙ НАВИГАЦИИ
        context["current_sidebar_key"] = "psychologist-match"

        return context
