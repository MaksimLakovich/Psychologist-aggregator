from django.urls import path

from calendar_engine._web.views.psychologist.working_schedule_page import \
    PsychologistWorkingSchedulePageView
from calendar_engine.apps import AppCalendarConfig

app_name = AppCalendarConfig.name

urlpatterns = [

    # === СПЕЦИАЛИСТ ===
    # 1) Рабочее расписание
    path(
        "psychologist-account/working-schedule/",
        PsychologistWorkingSchedulePageView.as_view(),
        name="psychologist-working-schedule",
    ),

]
