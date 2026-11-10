from django.http import Http404, JsonResponse
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    ParseError,
    ValidationError,
)
from rest_framework.views import exception_handler


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Операція суперечить поточному стану даних."
    default_code = "conflict"


def get_or_404(model, pk, what):
    try:
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise NotFound(f"{what} з id={pk} не знайдено.") from None


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    details = None
    if isinstance(exc, ValidationError):
        message = "Некоректні дані."
        details = response.data
    elif isinstance(exc, ParseError):
        message = "Некоректний JSON у тілі запиту."
    elif isinstance(exc, Http404):
        message = "Ресурс не знайдено."
    else:
        message = str(exc.detail)

    body = {"error": message}
    if details is not None:
        body["details"] = details
    response.data = body
    return response


def server_error(request):
    return JsonResponse(
        {"error": "Внутрішня помилка сервера. Спробуйте пізніше."}, status=500
    )
