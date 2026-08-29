from django.urls import path

from games import views

urlpatterns = [
    path("solo", views.start_solo_attempt, name="solo-attempt-start"),
    path("solo/<int:attempt_id>", views.solo_attempt_detail, name="solo-attempt-detail"),
    path(
        "solo/<int:attempt_id>/answers",
        views.submit_solo_answer,
        name="solo-answer-submit",
    ),
    path(
        "solo/<int:attempt_id>/complete",
        views.complete_solo_attempt,
        name="solo-attempt-complete",
    ),
]

