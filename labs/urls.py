from django.urls import path

from . import lab01, views

urlpatterns = [
    path("health/", views.Health.as_view()),
    path("01/bad/", lab01.PostListBad.as_view()),
    path("01/good/", lab01.PostListGood.as_view()),
    path("01/trap/", lab01.PostListTrap.as_view()),
    path("01/trap-fixed/", lab01.PostListTrapFixed.as_view()),
]