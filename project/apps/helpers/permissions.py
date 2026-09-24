from apps.user.models.user import RoleChoices
from rest_framework import permissions


class IsSuperUser(permissions.IsAdminUser):
    def has_permission(self, request, view):
        return bool(
            request.user
            and (
                request.user.is_superuser or request.user.role == RoleChoices.SUPERUSER
            )
        )


class IsAdministratorOrSuperUser(permissions.IsAdminUser):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.role in (RoleChoices.ADMINISTRATOR, RoleChoices.SUPERUSER)
        )


class IsPerformerTaskUser(permissions.IsAdminUser):
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == RoleChoices.PERFORMER_TASK)
