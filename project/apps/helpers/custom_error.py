from rest_framework import status
from rest_framework.exceptions import APIException, _get_error_details  # noqa: WPS450


class CustomValidationError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "A server error occurred."

    def __init__(self, detail, status_code):  # noqa: D107
        if status_code is not None:
            self.status_code = status_code  # noqa: WPS601
        if detail is None:
            detail = self.default_detail

        if not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        self.detail = _get_error_details(detail, status_code)
