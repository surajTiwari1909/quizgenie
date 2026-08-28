from django.urls import path

from users import views

urlpatterns = [
    path("signup", views.signup, name="signup"),
    path("signin", views.signin, name="signin"),
    path("token/refresh", views.refresh_token, name="token-refresh"),
    path("me", views.me, name="me"),
]
