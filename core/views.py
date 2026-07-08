from django.http import JsonResponse


def home(request):
    return JsonResponse(
        {"message": "Crocodile Maze backend работает"},
        json_dumps_params={"ensure_ascii": False},
    )
