from django.urls import path

from core.apps import CoreConfig
from core.views.start_view import StartPageView
from core.views.view_choice_psychologist import \
    ClientChoicePsychologistPageView
from core.views.view_general_questions import ClientGeneralQuestionsPageView
from core.views.view_personal_questions import ClientPersonalQuestionsPageView

app_name = CoreConfig.name

urlpatterns = [
    path("", StartPageView.as_view(), name="start-page"),
    path("general-questions/", ClientGeneralQuestionsPageView.as_view(), name="general-questions"),
    path("personal-questions/", ClientPersonalQuestionsPageView.as_view(), name="personal-questions"),
    path("choice-psychologist/", ClientChoicePsychologistPageView.as_view(), name="choice-psychologist"),
]
