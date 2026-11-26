from django.urls import path

from .views import current_user, login_view, refresh_view, csrf_cookie_view, logout_view

urlpatterns = [
    path("me/", current_user, name="current-user"),
    path("login/", login_view, name="login"),
    path("refresh/", refresh_view, name="refresh"),
    path("csrf/", csrf_cookie_view, name="csrf-cookie"),
    path("logout/", logout_view, name="logout"),
]
