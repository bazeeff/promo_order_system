from apps.user.models import User


class UserManager:
    def get_queryset(self, user, queryset=None):
        if queryset is None:
            queryset = User.objects.all()
        # filtering by user
        return queryset
