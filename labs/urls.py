from django.urls import path

from . import lab01, lab02, views

urlpatterns = [
    path("health/", views.Health.as_view()),
    path("01/bad/", lab01.PostListBad.as_view()),
    path("01/good/", lab01.PostListGood.as_view()),
    path("01/trap/", lab01.PostListTrap.as_view()),
    path("01/trap-fixed/", lab01.PostListTrapFixed.as_view()),
    path("02/bad/", lab02.PostByDateBad.as_view()),
    path("02/good/", lab02.PostByDateGood.as_view()),
]