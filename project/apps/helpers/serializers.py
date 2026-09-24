from drf_yasg import openapi
from rest_framework import serializers


class EagerLoadingSerializerMixin:
    select_related_fields = []
    prefetch_related_fields = []

    @classmethod
    def setup_eager_loading(cls, queryset):
        if cls.select_related_fields:
            queryset = queryset.select_related(*cls.select_related_fields)
        if cls.prefetch_related_fields:
            queryset = queryset.prefetch_related(*cls.prefetch_related_fields)
        return queryset


class EmptySerializer(serializers.Serializer):
    pass  # noqa: WPS420 WPS604


class EnumSerializer(serializers.Serializer):
    value = serializers.CharField()  # noqa: WPS110
    name = serializers.CharField(source="label")


class EnumField(serializers.ChoiceField):
    class Meta:
        pass  # noqa: WPS420 WPS604

    def __init__(self, enum_class, *args, **kwargs):  # noqa: D107
        EnumField.Meta.swagger_schema_fields = {
            "type": openapi.TYPE_OBJECT,
            "title": "Type",
            "properties": {
                "name": openapi.Schema(
                    title="Email subject",
                    type=openapi.TYPE_STRING,
                    enum=enum_class.labels,
                ),
                "value": openapi.Schema(
                    title="Значение",
                    type=openapi.TYPE_STRING,
                    enum=enum_class.values,
                ),
            },
        }
        self.enum_class = enum_class
        super().__init__(*args, choices=enum_class.choices, **kwargs)

    def to_representation(self, value):  # noqa: WPS110
        return EnumSerializer(self.enum_class[value.upper()]).data if value else None


class DeleteBatchRequestSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.UUIDField())  # noqa: WPS110


class DeleteBatchSerializer(serializers.Serializer):
    def get_fields(self):
        fields = super().get_fields()
        fields["items"] = serializers.PrimaryKeyRelatedField(
            queryset=self.context["queryset"], many=True
        )
        return fields


class CompanyAdminsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class RichTextUploadingFieldSerializer(serializers.Field):
    """Сериализатор подменяет относительный путь на абсолютный для картинок ckeditor."""

    pattern = 'src="/media/ckeditor_uploads/'

    def to_representation(self, text):
        request = self.context.get("request")

        if not request:
            return text

        scheme = "https" if request.is_secure() else "http"
        host = f"{scheme}://{request.get_host()}"
        replaced = f'src="{host}/media/ckeditor_uploads/'
        return text.replace(self.pattern, replaced)
