from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import GameInfoSerializer


def home(request):
    return JsonResponse(
        {"message": "Crocodile Maze backend работает"},
        json_dumps_params={"ensure_ascii": False},
    )


@extend_schema(
    summary="Информация об игре",
    description="Возвращает основную информацию об игре Crocodile Maze",
    responses=GameInfoSerializer,
)
@api_view(["GET"])
def game_info(request):
    return Response({
        "name": "Лабиринт Крокодила",
        "message": "API работает"
    })
