from rest_framework.exceptions import APIException


class ServiceError(APIException):
    status_code = 400
    default_detail = "Ошибка в работе сервиса"
    default_code = "service_error"


class AbstractService:
    """Родитель всех сервисов, все сервисы в системе должны наследоваться от него."""

    def process(self, *args, **kwargs):
        raise NotImplementedError("Should implement this error")
