from django.urls import path

from . import views
from . import lab01

urlpatterns = [
    path("health/", views.Health.as_view()),
    path("01/bad/", lab01.PostListBad.as_view()),
]