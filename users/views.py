from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import CurrentUserSerializer, LoginSerializer


@extend_schema(summary="Текущий пользователь", responses=CurrentUserSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    serializer = CurrentUserSerializer(request.user)
    return Response(serializer.data)


def token_response(access: str, refresh: str) -> Response:
    response = Response(
        {"access": access},
        headers={"Cache-Control": "no-store"},
    )
    response.set_cookie(
        key="refresh",
        value=refresh,
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/api/auth/",
    )
    return response


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
    return token_response(access=str(refresh.access_token), refresh=str(refresh))


@extend_schema(summary="Обновить токены", request=None)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@csrf_protect
def refresh_view(request):
    raw_refresh = request.COOKIES.get("refresh", "")

    try:
        token = RefreshToken(raw_refresh)

        with transaction.atomic():
            OutstandingToken.objects.select_for_update().get(
                jti=token[api_settings.JTI_CLAIM]
            )
            serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
            serializer.is_valid(raise_exception=True)

    except (TokenError, AuthenticationFailed, OutstandingToken.DoesNotExist, User.DoesNotExist):
        return Response(
            {"detail": "Войди снова, чтобы обновить токены."},
            status=401,
            headers={"WWW-Authenticate": 'Bearer realm="api"'},
        )

    tokens = serializer.validated_data
    return token_response(access=tokens["access"], refresh=tokens["refresh"])
