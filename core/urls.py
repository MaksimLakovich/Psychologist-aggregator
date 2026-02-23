from django.urls import path

from core.apps import CoreConfig
from core.views.client.my_account.main_account_page import ClientAccountView
from core.views.client.my_account.ps_catalog import (
    PsychologistCatalogDetailPageView,
    PsychologistCatalogPageView,
)
from core.views.client.my_account.questions_answers import CommonQuestionPageView
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
    # КЛИЕНТ: общая стартовая страница + общие информативные
    path("", StartPageView.as_view(), name="start-page"),
    path("faq/", CommonQuestionPageView.as_view(), name="faq-page"),

    # КЛИЕНТ: этапы подбора/фильтрации необходимых специалистов
    path("general-questions/", ClientGeneralQuestionsPageView.as_view(), name="general-questions"),
    path("personal-questions/", ClientPersonalQuestionsPageView.as_view(), name="personal-questions"),
    path("choice-psychologist/", ClientChoicePsychologistPageView.as_view(), name="choice-psychologist"),
    path("payment-card/", ClientAddPaymentCardPageView.as_view(), name="payment-card"),

    # КЛИЕНТ: работа с профилем
    path("client-account/", ClientAccountView.as_view(), name="client-account"),

    # КЛИЕНТ: каталог психологов
    # Важно: используем именно маршрут psychologist_catalog/ согласно согласованным требованиям.
    path("psychologist_catalog/", PsychologistCatalogPageView.as_view(), name="psychologist-catalog"),
    path(
        "psychologist_catalog/<slug:profile_slug>/",
        PsychologistCatalogDetailPageView.as_view(),
        name="psychologist-catalog-detail",
    ),
]
