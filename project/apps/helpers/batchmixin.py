import logging

from apps.helpers.serializers import DeleteBatchRequestSerializer, DeleteBatchSerializer
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger()


class DeleteBatchMixin:
    @swagger_auto_schema(request_body=DeleteBatchRequestSerializer)
    @action(methods=["post"], detail=False, url_path="delete-batch")
    def delete_batch(self, request):
        queryset = self.get_queryset()
        serializer = DeleteBatchSerializer(
            data=request.data, context={"queryset": queryset}
        )
        serializer.is_valid(raise_exception=True)
        errors = []
        for item in serializer.validated_data["items"]:  # noqa: WPS110
            try:
                item.delete()
            except Exception as e:
                errors.append(str(e))
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
