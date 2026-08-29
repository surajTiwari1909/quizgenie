from django.urls import path

from quizzes import views

urlpatterns = [
    path("", views.quiz_collection, name="quiz-list"),
    path("generate/topic", views.generate_topic_quiz, name="quiz-generate-topic"),
    path("generate/document", views.generate_document_quiz, name="quiz-generate-document"),
    path("<int:quiz_id>", views.quiz_detail, name="quiz-detail"),
    path("<int:quiz_id>/manage", views.quiz_manage, name="quiz-manage"),
    path("<int:quiz_id>/retry", views.retry_quiz_generation, name="quiz-retry"),
]
