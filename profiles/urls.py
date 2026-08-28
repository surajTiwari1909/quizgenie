from django.urls import path

from profiles import views

urlpatterns = [
    path("me/picture", views.profile_picture, name="profile-picture"),
]
