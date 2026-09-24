from rest_framework import serializers


class BasicCeleryResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    result = serializers.SerializerMethodField()  # noqa: WPS110

    def get_result(self, obj):  # noqa: WPS110
        try:  # noqa: WPS229
            if issubclass(obj.result.__class__, Exception):
                return str(obj.result)
            return obj.result
        except Exception as e:
            return str(e)
