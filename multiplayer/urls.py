from django.urls import path

from multiplayer import views

urlpatterns = [
    path("contests", views.create_contest, name="contest-create"),
    path("contests/join", views.join_contest, name="contest-join"),
    path("contests/<int:contest_id>", views.contest_detail, name="contest-detail"),
    path("contests/<int:contest_id>/start", views.start_contest, name="contest-start"),
    path("contests/<int:contest_id>/answers", views.contest_answer, name="contest-answer"),
    path("contests/<int:contest_id>/finish", views.finish_contest, name="contest-finish"),
]
