from api.v1.user.serializers import (
    UserCompactSerializer,
    UserReadSerializer,
    UserRegistrationSerializer,
    UserWriteSerializer,
)
from apps.helpers import exceptions, viewsets
from apps.helpers.permissions import (
    IsAdministratorOrSuperUser,
    IsPerformerTaskUser,
    IsSuperUser,
)
from apps.helpers.serializers import EnumSerializer
from apps.user.managers import UserManager
from apps.user.models.user import RoleChoices
from django.contrib.auth import logout
from django.core.exceptions import ObjectDoesNotExist
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import authentication, decorators, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt import authentication as authentication_jwt
from rest_framework_simplejwt import serializers as jwt_serializers
from rest_framework_simplejwt import views


class AuthViewSet(
    viewsets.RUDExtendedModelViewSet, views.TokenViewBase
):  # noqa: WPS214
    serializer_class = UserReadSerializer
    serializer_class_map = {
        "login": jwt_serializers.TokenObtainPairSerializer,
        "refresh": jwt_serializers.TokenRefreshSerializer,
        "registration": UserRegistrationSerializer,
    }
    permission_classes = (permissions.IsAuthenticated,)
    permission_map = {
        "login": permissions.AllowAny,
        "refresh": permissions.AllowAny,
        "registration": permissions.AllowAny,
    }
    authentication_classes = (
        authentication_jwt.JWTAuthentication,
        authentication.SessionAuthentication,
    )

    default_responses = {
        400: exceptions.ErrorResponseSerializer,
        410: exceptions.ErrorResponseSerializer,
    }

    def get_queryset(self):  # noqa: WPS615
        user = self.request.user
        queryset = UserManager().get_queryset(user)
        if not user.is_authenticated:
            return queryset.none()

        return queryset

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: jwt_serializers.TokenObtainPairSerializer}
    )
    @decorators.action(methods=["post"], detail=False)
    def login(self, request):
        return super().post(request)  # noqa: WPS613

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: jwt_serializers.TokenObtainPairSerializer}
    )
    @decorators.action(methods=["post"], detail=False)
    def refresh(self, request):
        """Обновление токена."""
        return super().post(request)  # noqa: WPS613

    @swagger_auto_schema(
        request_body=no_body, responses={status.HTTP_200_OK: "No content"}
    )
    @decorators.action(methods=["post"], detail=False)
    def logout(self, request):
        try:
            request.user.auth_token.delete()
        except (AttributeError, ObjectDoesNotExist):
            pass  # noqa: WPS420

        logout(request)
        return Response(status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=UserRegistrationSerializer,
        responses={
            201: UserReadSerializer,
            400: exceptions.BadRequestResponseSerializer,
        },
    )
    @action(methods=["post"], detail=False)
    def registration(self, request):
        """Регистрация пользователя."""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = UserReadSerializer(
            instance=user, context=self.get_serializer_context()
        ).data  # noqa: WPS110
        return Response(data, status=status.HTTP_201_CREATED)


class UserViewSet(AuthViewSet):  # noqa: WPS214
    serializer_class = UserReadSerializer
    serializer_class_map = {
        **AuthViewSet.serializer_class_map,
        "list": UserReadSerializer,
        "retrieve": UserReadSerializer,
        "me": UserReadSerializer,
        "create": UserWriteSerializer,
        "compact": UserCompactSerializer,
        "update": UserWriteSerializer,
        "partial_update": UserWriteSerializer,
    }
    permission_classes = (permissions.IsAuthenticated,)
    permission_map = {
        **AuthViewSet.permission_map,
        "create": (IsSuperUser,),
        "list": (IsAdministratorOrSuperUser,),
        "retrieve": (IsAdministratorOrSuperUser,),
        "destroy": (IsAdministratorOrSuperUser,),
        "password_reset": (
            IsAdministratorOrSuperUser,
            IsSuperUser,
            IsPerformerTaskUser,
        ),
    }

    search_fields = ("first_name",)
    ordering_fields = ("first_name",)

    default_responses = {
        400: exceptions.ErrorResponseSerializer,
        410: exceptions.ErrorResponseSerializer,
    }

    def get_queryset(self):  # noqa: WPS615
        user = self.request.user
        queryset = UserManager().get_queryset(user)
        if not user.is_authenticated:
            return queryset.none()

        return queryset

    @decorators.action(methods=["get"], detail=False)
    def me(self, request, **kwargs):
        """Получение информации о залогинненом юзере."""
        serializer = self.get_serializer(instance=request.user)
        return Response(serializer.data)

    @decorators.action(methods=["get"], detail=False)
    def compact(self, request):
        """List compact user."""
        return super().list(request)  # noqa: WPS613

    @swagger_auto_schema(
        request_body=UserWriteSerializer,
        responses={
            200: UserReadSerializer,
            400: exceptions.ErrorResponseSerializer,
        },
    )
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # noqa:  WPS204
        user = serializer.save()
        data = UserReadSerializer(
            instance=user, context=self.get_serializer_context()
        ).data  # noqa: WPS110
        return Response(data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(responses={200: EnumSerializer})
    @action(methods=["get"], detail=False)
    def role(self, request):
        """Возвращает возможные роли"""
        return Response(EnumSerializer(RoleChoices, many=True).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user == instance:
            raise ValidationError("Нельзя удалить собственную учетную запись")
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
