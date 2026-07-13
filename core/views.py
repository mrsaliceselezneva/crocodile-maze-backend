from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response


def home(request):
    return JsonResponse(
        {"message": "Crocodile Maze backend работает"},
        json_dumps_params={"ensure_ascii": False},
    )


@api_view(["GET"])
def game_info(request):
    return Response({
        "name": "Лабиринт Крокодила",
        "message": "API работает"
    })
