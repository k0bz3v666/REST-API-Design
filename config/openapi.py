from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse
from rest_framework import serializers


class ApiErrorSerializer(serializers.Serializer):
    error = serializers.CharField(help_text="Зрозуміле повідомлення про помилку.")


class ApiValidationErrorSerializer(ApiErrorSerializer):
    details = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        help_text="Помилки валідації по полях: назва поля -> список повідомлень.",
    )


def error_response(description, message):
    return OpenApiResponse(
        response=ApiErrorSerializer,
        description=description,
        examples=[
            OpenApiExample(
                "Приклад", value={"error": message}, response_only=True
            )
        ],
    )


BAD_REQUEST = OpenApiResponse(
    response=ApiValidationErrorSerializer,
    description="Некоректні дані або параметри запиту.",
    examples=[
        OpenApiExample(
            "Помилка валідації",
            value={
                "error": "Некоректні дані.",
                "details": {"name": ["Це поле обов'язкове."]},
            },
            response_only=True,
        )
    ],
)

UNAUTHORIZED = error_response(
    "Немає access токена, він недійсний або прострочений.",
    "Потрібна авторизація. Передайте access токен у заголовку "
    "Authorization: Bearer <token>.",
)

FORBIDDEN = error_response(
    "Користувач авторизований, але не є адміністратором.",
    "Змінювати каталог можуть лише адміністратори.",
)


ADMIN_ERRORS = {401: UNAUTHORIZED, 403: FORBIDDEN}


OPTIONAL_AUTH = [{"jwtAuth": []}, {}]


def not_found(what):
    return error_response(
        "Об'єкта з таким id не існує.", f"{what} з id=999 не знайдено."
    )


def conflict(message):
    return error_response("Дія суперечить поточному стану даних.", message)


def pk_param(description):
    return OpenApiParameter(
        name="pk",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.PATH,
        description=description,
    )
