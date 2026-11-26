from django.conf import settings
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import CurrentUserSerializer, LoginSerializer


@extend_schema(summary="Текущий пользователь", responses=CurrentUserSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    serializer = CurrentUserSerializer(request.user)
    return Response(serializer.data)


@extend_schema(summary="Вход по хендлу и паролю", request=LoginSerializer)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@csrf_protect
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = authenticate(request=request, **serializer.validated_data)
    if user is None or not user.is_active:
        return Response(
            {"detail": "Неверный логин или пароль."},
            status=401,
            headers={"WWW-Authenticate": 'Bearer realm="api"'},
        )

    refresh = RefreshToken.for_user(user)
    response = Response(
        {"access": str(refresh.access_token)},
        headers={"Cache-Control": "no-store"},
    )
    response.set_cookie(
        key="refresh",
        value=str(refresh),
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/api/auth/",
    )
    return response
