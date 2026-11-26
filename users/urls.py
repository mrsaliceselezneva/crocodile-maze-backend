from django.urls import path

from .views import current_user, login_view

urlpatterns = [
    path("me/", current_user, name="current-user"),
    path("login/", login_view, name="login"),
]
