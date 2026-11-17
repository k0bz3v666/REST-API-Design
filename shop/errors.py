import logging

from django.http import Http404, JsonResponse
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied,
    ValidationError,
)
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken


logger = logging.getLogger(__name__)


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Операція суперечить поточному стану даних."
    default_code = "conflict"


def get_or_404(model, pk, what):
    try:
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise NotFound(f"{what} з id={pk} не знайдено.") from None


def describe_actor(request):
    try:
        user = request.user
        if user.is_authenticated:
            return f"user_id={user.pk}"
    except Exception:
        return "unknown"
    return "anonymous"


def log_api_error(exc, response, context, details=None):
    request = context.get("request")
    if request is None:
        return
    line = "%s %s -> %s (%s): %s" % (
        request.method,
        request.path,
        response.status_code,
        describe_actor(request),
        type(exc).__name__,
    )
    if isinstance(details, dict):
        line += " fields=%s" % sorted(details)
    if response.status_code >= 500:
        logger.error(line)
    elif response.status_code in (401, 403, 409):
        logger.warning(line)
    else:
        logger.debug(line)


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
    elif isinstance(exc, InvalidToken):


        message = "Токен недійсний або його термін дії закінчився."
    elif isinstance(exc, NotAuthenticated):
        message = (
            "Потрібна авторизація. Передайте access токен у заголовку "
            "Authorization: Bearer <token>."
        )
    elif isinstance(exc, (AuthenticationFailed, PermissionDenied)):
        message = str(exc.detail)
    else:
        message = str(exc.detail)

    body = {"error": message}
    if details is not None:
        body["details"] = details
    response.data = body
    log_api_error(exc, response, context, details)
    return response


def server_error(request):
    return JsonResponse(
        {"error": "Внутрішня помилка сервера. Спробуйте пізніше."}, status=500
    )
