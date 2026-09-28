import hashlib
import json

from api.v1.order.filters import (
    GoodFilterSet,
    OrderFilterSet,
    PromoCodeFilterSet,
)
from api.v1.order.serializers import (
    CategorySerializer,
    CategoryWriteSerializer,
    GoodSerializer,
    GoodWriteSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    PromoCodeSerializer,
    PromoCodeWriteSerializer,
)
from apps.helpers import exceptions, viewsets
from apps.helpers.permissions import IsAdministratorOrSuperUser
from apps.order.models import Category, Good, Order, PromoCode
from apps.order.services import OrderCreationService
from apps.user.models.user import RoleChoices
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
IDEMPOTENCY_KEY_MAX_LENGTH = 128


def make_request_fingerprint(request) -> str:
    """Отпечаток тела запроса для проверки идемпотентности."""
    canonical = json.dumps(
        request.data,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def get_idempotency_key(request):
    """Достать заголовок Idempotency-Key; пустое значение — как отсутствующий."""
    key = (request.headers.get(IDEMPOTENCY_KEY_HEADER) or "").strip()
    if len(key) > IDEMPOTENCY_KEY_MAX_LENGTH:
        raise ValidationError(
            {IDEMPOTENCY_KEY_HEADER: "Ключ идемпотентности длиннее 128 символов."}
        )
    return key or None


class OrderCreateView(APIView):
    """Создание заказа с опциональным промокодом.

    Пользователь определяется аутентификацией. Повторный запрос с тем же
    заголовком Idempotency-Key и тем же телом возвращает уже созданный
    заказ со статусом 200; с другим телом — 409.
    """

    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(
        request_body=OrderCreateSerializer,
        responses={
            status.HTTP_200_OK: OrderSerializer,
            status.HTTP_201_CREATED: OrderSerializer,
            status.HTTP_400_BAD_REQUEST: exceptions.BadRequestResponseSerializer,
            status.HTTP_409_CONFLICT: exceptions.ErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order, replayed = OrderCreationService().process(
            user=request.user,
            items=serializer.validated_data["items"],
            promocode=serializer.validated_data.get("promocode"),
            idempotency_key=get_idempotency_key(request),
            request_fingerprint=make_request_fingerprint(request),
        )
        data = OrderSerializer(
            instance=order,
            context={"request": request},
        ).data
        return Response(
            data,
            status=(
                status.HTTP_200_OK
                if replayed
                else status.HTTP_201_CREATED
            ),
        )


class CategoryViewSet(viewsets.ExtendedModelViewSet):
    """CRUD категорий товаров."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    serializer_class_map = {
        "create": CategoryWriteSerializer,
        "update": CategoryWriteSerializer,
        "partial_update": CategoryWriteSerializer,
    }
    permission_classes = (permissions.IsAuthenticated,)
    permission_map = {
        "create": (IsAdministratorOrSuperUser,),
        "update": (IsAdministratorOrSuperUser,),
        "partial_update": (IsAdministratorOrSuperUser,),
        "destroy": (IsAdministratorOrSuperUser,),
    }
    search_fields = ("name",)


class GoodViewSet(viewsets.ExtendedModelViewSet):
    """CRUD товаров каталога."""

    queryset = Good.objects.all()
    serializer_class = GoodSerializer
    serializer_class_map = {
        "create": GoodWriteSerializer,
        "update": GoodWriteSerializer,
        "partial_update": GoodWriteSerializer,
    }
    permission_classes = (permissions.IsAuthenticated,)
    permission_map = {
        "create": (IsAdministratorOrSuperUser,),
        "update": (IsAdministratorOrSuperUser,),
        "partial_update": (IsAdministratorOrSuperUser,),
        "destroy": (IsAdministratorOrSuperUser,),
    }
    filterset_class = GoodFilterSet
    search_fields = ("name",)
    ordering_fields = ("name", "price", "created_at")


class PromoCodeViewSet(viewsets.ExtendedModelViewSet):
    """CRUD промокодов; счётчик использований управляется сервисом заказов."""

    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    serializer_class_map = {
        "create": PromoCodeWriteSerializer,
        "update": PromoCodeWriteSerializer,
        "partial_update": PromoCodeWriteSerializer,
    }
    permission_classes = (permissions.IsAuthenticated,)
    permission_map = {
        "create": (IsAdministratorOrSuperUser,),
        "update": (IsAdministratorOrSuperUser,),
        "partial_update": (IsAdministratorOrSuperUser,),
        "destroy": (IsAdministratorOrSuperUser,),
    }
    filterset_class = PromoCodeFilterSet
    search_fields = ("code",)


class OrderViewSet(viewsets.LRExtendedModelViewSet):
    """Просмотр заказов.

    Обычные пользователи видят только свои заказы; администраторы и
    суперпользователи — все, с фильтром ``?user=<id>``.
    """

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_class = OrderFilterSet
    ordering_fields = ("created_at", "subtotal", "total")

    def get_queryset(self):  # noqa: WPS615
        queryset = super().get_queryset()
        if not self._is_staff(self.request.user):
            queryset = queryset.filter(user=self.request.user)
        return queryset

    @staticmethod
    def _is_staff(user) -> bool:
        return user.is_superuser or user.role in (
            RoleChoices.ADMINISTRATOR,
            RoleChoices.SUPERUSER,
        )
