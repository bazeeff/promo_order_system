import re

from rest_framework.exceptions import ValidationError


def username_validator(data):  # noqa: D103, WPS110
    if data.get("last_name") and not re.search(r"^[А-Я-а-я]*\Z", data["last_name"]):
        raise ValidationError(
            {"last_name": ["Поле должно содержать буквы русского алфавита"]}
        )

    if data.get("first_name") and not re.search(r"^[А-Я-а-я]*\Z", data["first_name"]):
        raise ValidationError(
            {"first_name": ["Поле должно содержать буквы русского алфавита"]}
        )
