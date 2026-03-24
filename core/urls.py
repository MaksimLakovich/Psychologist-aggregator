from django.urls import path

from core.apps import CoreConfig
from core.views.client.my_account.main_account_page import ClientAccountView
from core.views.client.my_account.events_page import \
    ClientEventsView
from core.views.client.my_account.ps_catalog import (
    PsychologistCardDetailPageView, PsychologistCatalogFilterAjaxView,
    PsychologistCatalogPageView)
from core.views.client.my_account.questions_answers import \
    CommonQuestionPageView
from core.views.client.my_account.therapy_session_detail_page import \
    ClientTherapySessionDetailView
from core.views.client.specialist_matching.view_choice_psychologist import \
    ClientChoicePsychologistPageView
from core.views.client.specialist_matching.view_general_questions import \
    ClientGeneralQuestionsPageView
from core.views.client.specialist_matching.view_payment_card import \
    ClientAddPaymentCardPageView
from core.views.client.specialist_matching.view_personal_questions import \
    ClientPersonalQuestionsPageView
from core.views.start_view import StartPageView

app_name = CoreConfig.name

urlpatterns = [
    # Общая стартовая страница + разные общие информативные страницы приложения
    path("", StartPageView.as_view(), name="start-page"),
    path("faq/", CommonQuestionPageView.as_view(), name="faq-page"),

    # Этапы подбора/фильтрации необходимых специалистов по заданным клиентом параметрам
    path("general-questions/", ClientGeneralQuestionsPageView.as_view(), name="general-questions"),
    path("personal-questions/", ClientPersonalQuestionsPageView.as_view(), name="personal-questions"),
    path("choice-psychologist/", ClientChoicePsychologistPageView.as_view(), name="choice-psychologist"),
    path("payment-card/", ClientAddPaymentCardPageView.as_view(), name="payment-card"),

    # Работа с КАТАЛОГОМ психологов
    path("psychologist_catalog/", PsychologistCatalogPageView.as_view(), name="psychologist-catalog"),

    # AJAX для каталога: фильтры
    path(
        "psychologist_catalog/filter/",
        PsychologistCatalogFilterAjaxView.as_view(),
        name="psychologist-catalog-filter"
    ),

    # Работа с личным КАБИНЕТОМ
    path("client-account/", ClientAccountView.as_view(), name="client-account"),
    path("client-account/events/", ClientEventsView.as_view(), name="client-events"),
    path(
        "client-account/sessions/<uuid:event_id>/",
        ClientTherapySessionDetailView.as_view(),
        name="client-therapy-session-detail",
    ),

    # Детальная карточка психолога в КАТАЛОГЕ должна быть последней, потому что это catch-all slug route.
    # Если поставить ее выше конкретных URL, например "client-account/", Django начнет ошибочно
    # воспринимать такие адреса как profile_slug.
    path("<slug:profile_slug>/", PsychologistCardDetailPageView.as_view(), name="psychologist-card-detail"),

]
