from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q  # noqa: WPS347

User = get_user_model()


class MultipleFieldsAuthBackend(ModelBackend):
    def authenticate(self, request, password=None, username=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return  # noqa: WPS324

        try:
            user = User.objects.get(Q(username=username) | Q(email=username))
        except User.DoesNotExist:
            User().set_password(password)
        else:
            if user.check_password(password):
                return user
