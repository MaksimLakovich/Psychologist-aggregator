from django.urls import path

from core.apps import CoreConfig
from core.views.home_client_general_questions import \
    ClientGeneralQuestionsPageView
from core.views.start_view import StartPageView

app_name = CoreConfig.name

urlpatterns = [
    path("", StartPageView.as_view(), name="start_page"),
    path("general-questions/", ClientGeneralQuestionsPageView.as_view(), name="client_general_questions_page"),
]
