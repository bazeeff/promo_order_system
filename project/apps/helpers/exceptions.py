from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as base_exception_handler
from rest_framework.exceptions import APIException


class BadRequestResponseSerializer(serializers.Serializer):
    status_code = serializers.IntegerField()
    errors = serializers.DictField(child=serializers.ListField())


class ErrorResponseSerializer(serializers.Serializer):
    status_code = serializers.IntegerField()
    errors = serializers.CharField()


def exception_handler(exc, context):
    """Обработчик ошибок."""
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(detail=as_serializer_error(exc))

    response = base_exception_handler(exc, context)
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if response is not None:
        data = {  # noqa: WPS110
            "status_code": exc.status_code,
            "errors": {},
        }
        if isinstance(exc.detail, list):
            data["errors"] = exc.detail
        elif isinstance(exc.detail, dict):
            data["errors"] = exc.detail
        else:
            data["errors"] = exc.detail
        response.data = data
    return response

class IdempotencyConflict(APIException):
    status_code = 409
    default_detail = "Idempotency-Key was already used with a different request body."
    default_code = "idempotency_conflict"


class PromoAlreadyUsed(APIException):
    status_code = 409
    default_detail = "This user has already used this promo code."
    default_code = "promo_already_used"


class PromoUsageLimitReached(APIException):
    status_code = 409
    default_detail = "Promo code usage limit has been reached."
    default_code = "promo_usage_limit_reached"


class PromoNotFound(APIException):
    status_code = 404
    default_detail = "Promo code does not exist."
    default_code = "promo_not_found"


class PromoInactive(APIException):
    status_code = 400
    default_detail = "Promo code is deactivated."
    default_code = "promo_inactive"


class PromoExpired(APIException):
    status_code = 400
    default_detail = "Promo code has expired."
    default_code = "promo_expired"


class PromoNotApplicable(APIException):
    status_code = 400
    default_detail = "Promo code does not apply to any item in the order."
    default_code = "promo_not_applicable"
