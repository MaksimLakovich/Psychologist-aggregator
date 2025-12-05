from django.urls import path

from core.apps import CoreConfig
from core.views.start_view import StartPageView
from core.views.view_general_questions import ClientGeneralQuestionsPageView
from core.views.view_personal_questions import ClientPersonalQuestionsPageView

app_name = CoreConfig.name

urlpatterns = [
    path("", StartPageView.as_view(), name="start_page"),
    path("general-questions/", ClientGeneralQuestionsPageView.as_view(), name="client_general_questions_page"),
    path("personal-questions/", ClientPersonalQuestionsPageView.as_view(), name="client_personal_questions_page"),
]
