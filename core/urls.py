from django.urls import path

from core.apps import CoreConfig
from core.views.home_page import HomePageView

app_name = CoreConfig.name

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
]
