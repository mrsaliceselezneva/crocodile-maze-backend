from django.urls import path

from .views import home, game_info

urlpatterns = [
    path("api/health/", home, name="health"),
    path("api/game-info/", game_info)
]
