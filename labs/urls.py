from django.urls import path

from . import lab01, lab02, lab03, lab04, views

urlpatterns = [
    path("health/", views.Health.as_view()),
    path("01/bad/", lab01.PostListBad.as_view()),
    path("01/good/", lab01.PostListGood.as_view()),
    path("01/trap/", lab01.PostListTrap.as_view()),
    path("01/trap-fixed/", lab01.PostListTrapFixed.as_view()),
    path("02/bad/", lab02.PostByDateBad.as_view()),
    path("02/good/", lab02.PostByDateGood.as_view()),
    path("03/bad/", lab03.HasCommentsBad.as_view()),
    path("03/good/", lab03.HasCommentsGood.as_view()),
    path("03/page-counted/", lab03.PostsPageCounted.as_view()),
    path("03/page-nocount/", lab03.PostsPageNoCount.as_view()),
    path("03/count-exact/", lab03.PostCountExact.as_view()),
    path("03/count-approx/", lab03.PostCountApprox.as_view()),
    path("04/full/", lab04.TitlesFull.as_view()),
    path("04/only/", lab04.TitlesOnly.as_view()),
    path("04/values/", lab04.TitlesValues.as_view()),
    path("04/defer-trap/", lab04.DeferTrap.as_view()),
]