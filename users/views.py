from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import logout as django_logout
from django.db import transaction
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework.authentication import SessionAuthentication
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
from .serializers import CurrentUserSerializer, LoginSerializer, AccessTokenResponseSerializer, DetailErrorSerializer

CSRF_HEADER = OpenApiParameter(
    name="X-CSRFToken",
    location=OpenApiParameter.HEADER,
    required=True,
    description="Значение cookie csrftoken, полученной через GET /api/auth/csrf/.",
)

CSRF_ERROR = OpenApiResponse(
    response=OpenApiTypes.STR,
    description="Запрос отклонён при проверке CSRF.",
)


@extend_schema(
    summary="Текущий пользователь",
    description="Передай access-токен в заголовке Authorization: Bearer <access>.",
    responses={
        200: CurrentUserSerializer,
        401: OpenApiResponse(
            response=DetailErrorSerializer,
            description="Требуется вход. Учётные данные отсутствуют или недействительны.",
        ),
    },
)
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


@extend_schema(
    summary="Вход по хендлу и паролю",
    description="При успешном входе устанавливает HttpOnly cookie refresh на 31 день.",
    request=LoginSerializer,
    parameters=[CSRF_HEADER],
    responses={
        200: AccessTokenResponseSerializer,
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description=(
                    "Ошибки полей приходят списками под ключами username или password. "
                    "При некорректном JSON сообщение находится в поле detail."
            ),
        ),
        401: OpenApiResponse(
            response=DetailErrorSerializer,
            description="Неверный логин или пароль либо аккаунт отключён.",
        ),
        (403, "text/html"): CSRF_ERROR,
    },
)
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


@extend_schema(summary="Получить CSRF-cookie",
               description="Устанавливает cookie csrftoken. Передай её значение в заголовке X-CSRFToken при входе, обновлении токенов и выходе.",
               responses={204: None})
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_cookie_view(request):
    return Response(status=204, headers={"Cache-Control": "no-store"})


@extend_schema(
    summary="Обновить токены",
    description="Сервер читает refresh из cookie и при успешном обмене устанавливает новую cookie на 31 день.",
    request=None,
    parameters=[CSRF_HEADER],
    responses={
        200: AccessTokenResponseSerializer,
        401: OpenApiResponse(
            response=DetailErrorSerializer,
            description="Refresh-cookie отсутствует, токен недействителен или аккаунт недоступен",
        ),
        (403, "text/html"): CSRF_ERROR,
    },
)
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


@extend_schema(
    summary="Выйти из аккаунта",
    description="Отзывает текущий refresh, удаляет его cookie и завершает Django-сессию.",
    request=None,
    parameters=[CSRF_HEADER],
    responses={
        204: OpenApiResponse(description="Выход выполнен. Тело ответа пустое."),
        (403, "text/html"): CSRF_ERROR,
        (403, "application/json"): OpenApiResponse(
            response=DetailErrorSerializer,
            description="Запрос отклонён при проверке CSRF.",
        ),
    },
)
@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
@csrf_protect
def logout_view(request):
    raw_refresh = request.COOKIES.get("refresh")
    if raw_refresh:
        try:
            token = RefreshToken(raw_refresh)
            with transaction.atomic():
                OutstandingToken.objects.select_for_update().get(
                    jti=token[api_settings.JTI_CLAIM]
                )
                token.blacklist()
        except (TokenError, OutstandingToken.DoesNotExist):
            # Повторный выход тоже должен очистить cookie.
            pass

    django_logout(request)
    response = Response(status=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie("refresh", path="/api/auth/", samesite="Lax")
    return response
