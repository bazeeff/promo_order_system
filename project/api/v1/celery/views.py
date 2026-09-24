from apps import app
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import BasicCeleryResultSerializer


class CeleryResultView(APIView):
    @swagger_auto_schema(
        responses={200: BasicCeleryResultSerializer},
    )
    def get(self, request, pk):
        """Роут возвращает результаты работы из селери.

        Поле status может иметь статусы SUCCESS, FAILURE, PENDING и другие. которые для фронта не важны.
        SUCCESS - задача выполнилась успешно.
        FAILURE - выполнение задачи завершилось ошибкой.
        PENDING - задача выполняется.
        В поле result - может быть что угодно. Сериализатор не даст вывести правильный возвращаемый тип.
        Может быть и строка и словарь и список и null и т.д.
        """
        serializer = BasicCeleryResultSerializer(app.AsyncResult(pk))
        return Response(serializer.data)
