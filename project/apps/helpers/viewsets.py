# flake8: noqa
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


def paginate_response(
    viewset, queryset=None, serializer_class=None, context=None, add_context=None
):
    if queryset is None:
        queryset = viewset.filter_queryset(viewset.get_queryset())

    serializer_class = serializer_class or viewset.get_serializer_class()
    context = context or viewset.get_serializer_context()
    if add_context:
        context.update(add_context)

    page = viewset.paginate_queryset(queryset)
    if page is not None:
        serializer = serializer_class(page, many=True, context=context)
        return viewset.get_paginated_response(serializer.data)

    serializer = serializer_class(queryset, many=True, context=context)
    return Response(serializer.data)


class ExtendViewSet:
    """This viewset mixin class with extended options list."""

    permission_map = {}
    throttle_scope_map = {}
    throttle_class_map = {}
    serializer_class_map = {}

    def get_queryset(self):
        queryset = super().get_queryset()
        serializer_class = self.get_serializer_class()(
            self.action, self.serializer_class
        )
        if hasattr(serializer_class, "setup_eager_loading"):
            queryset = serializer_class.setup_eager_loading(queryset)
        return queryset

    def get_serializer_class(self):
        self.serializer_class = self.serializer_class_map.get(
            self.action, self.serializer_class
        )
        return super().get_serializer_class()

    def initialize_request(self, request, *args, **kwargs):
        request = super().initialize_request(request, *args, **kwargs)
        throttle_scope = self.throttle_scope_map.get(self.action, None)
        throttle_class = self.throttle_class_map.get(self.action, None)
        cls_throttle_scope = getattr(self, "throttle_scope", None)
        cls_throttle = getattr(self, "throttle_classes", None)
        self.throttle_scope = throttle_scope or cls_throttle_scope or ""
        self.throttle_classes = throttle_class or cls_throttle
        return request

    def get_permissions(self):
        perms = self.permission_map.get(self.action, None)
        if perms and not isinstance(perms, (tuple, list)):
            perms = [perms]
        self.permission_classes = perms or self.permission_classes
        return super().get_permissions()


class ExtendedViewSet(ExtendViewSet, GenericViewSet):
    pass


class ExtendedModelViewSet(ExtendViewSet, viewsets.ModelViewSet):
    """
    Examples:
    class MyModelViewSet(ExtendedModelViewSet):
        serializer_class_map = {
            'list': ListMyModelSerializer,
            'retrieve': RetrieveMyModelSerializer,
            'update': UpdateMyModelSerializer,
            ...
        }
    """

    pass


class RUDExtendedModelViewSet(
    ExtendViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    pass


class CRDExtendedModelViewSet(
    ExtendViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    pass


class CRUExtendedModelViewSet(
    ExtendViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    pass


class ListExtendedModelViewSet(
    ExtendViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    pass


class CExtendedModelViewSet(
    ExtendViewSet,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    pass


class CRExtendedModelViewSet(
    ExtendViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    pass


class LRExtendedModelViewSet(
    ExtendViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    pass


class CRUDExtendedModelViewSet(
    ExtendViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    pass
