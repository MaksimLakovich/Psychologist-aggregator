from django.urls import path

from core.apps import CoreConfig
from core.views.home_view import HomePageView
from core.views.start_view import StartPageView

app_name = CoreConfig.name

urlpatterns = [
    path("", StartPageView.as_view(), name="start_page"),
    path("home/", HomePageView.as_view(), name="home_page"),
]
