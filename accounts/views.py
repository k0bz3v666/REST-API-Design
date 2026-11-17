import logging

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.openapi import BAD_REQUEST, UNAUTHORIZED, error_response

from .api_docs import (
    AccessTokenSerializer,
    CredentialsSerializer,
    RefreshTokenSerializer,
    TokenPairSerializer,
)
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

logger = logging.getLogger(__name__)


class RegisterView(APIView):


    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Реєстрація",
        description=(
            "Створює звичайного користувача (не адміністратора). Пароль у "
            "відповіді не повертається, у базі зберігається лише хеш."
        ),
        request=RegisterSerializer,
        responses={201: RegisterSerializer, 400: BAD_REQUEST},
        examples=[
            OpenApiExample(
                "Новий користувач",
                value={
                    "username": "olena",
                    "first_name": "Олена",
                    "last_name": "Коваль",
                    "email": "olena@example.com",
                    "password": "Str0ng-pass-42",
                    "password_confirm": "Str0ng-pass-42",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Створений користувач",
                value={
                    "id": 2,
                    "username": "olena",
                    "first_name": "Олена",
                    "last_name": "Коваль",
                    "email": "olena@example.com",
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("New user registered: user_id=%s", user.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

    @extend_schema(
        tags=["Auth"],
        summary="Логін",
        description="Перевіряє username і пароль, повертає пару JWT токенів.",
        request=CredentialsSerializer,
        responses={
            200: TokenPairSerializer,
            400: BAD_REQUEST,
            401: error_response(
                "Невірний username або пароль.", "Невірний username або пароль."
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        logger.info("User logged in: user_id=%s", response.data["user"]["id"])
        return response


class RefreshView(TokenRefreshView):
    @extend_schema(
        tags=["Auth"],
        summary="Оновити access токен",
        description=(
            "Приймає refresh токен і повертає новий access токен. Ротація "
            "refresh токенів не використовується."
        ),
        request=RefreshTokenSerializer,
        responses={
            200: AccessTokenSerializer,
            400: BAD_REQUEST,
            401: error_response(
                "Refresh токен недійсний, прострочений або це access токен.",
                "Токен недійсний або його термін дії закінчився.",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Поточний користувач",
        description="Хто зараз авторизований (потрібен access токен).",
        responses={200: UserSerializer, 401: UNAUTHORIZED},
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)
