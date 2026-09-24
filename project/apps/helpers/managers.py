# flake8: noqa
from django.contrib.auth.models import UserManager
from django.contrib.auth.models import UserManager as BaseUserManager
from django.db import models
from django.utils import timezone


# TODO need refactor, extra query
class DeletedQueryMixin(models.query.QuerySet):
    def delete(self, force=False):
        if force:
            return super().delete()
        else:
            return self._delete()

    def _delete(self):
        return (self.count(), self.update(deleted_at=timezone.now()))

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def non_deleted(self):
        return super().filter(deleted_at__isnull=True)


class DeletedQuerySet(DeletedQueryMixin, models.query.QuerySet):
    pass


class DeletedManager(models.Manager):
    def get_queryset(self):
        return DeletedQuerySet(self.model, using=self._db)

    def deleted(self):
        return self.get_queryset().filter(deleted_at__isnull=False)

    def non_deleted(self):
        return self.get_queryset().filter(deleted_at__isnull=True)


class UserDeletedManager(DeletedManager, BaseUserManager):
    def create_user(self, email, password=None, **other_fields):
        """
        Creates and saves a User with the given phone and password.
        """
        if not email:
            raise ValueError("Users must have an email")

        user = self.model(email=email, **other_fields)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **other_fields):
        """
        Creates and saves a superuser with the given phone and password.
        """
        user = self.create_user(email=email, password=password, **other_fields)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class CustomFieldUserManager(UserManager):
    def __init__(self, username_field_name=None, password_field_name=None):
        super().__init__()
        self.password_field_name = password_field_name or "password"
        self.username_field_name = username_field_name or "username"

    def _create_user(self, email, **fields):
        """
        Create and save a user with the given username_field_name, email, and password_field_name.
        """
        if not email:
            raise ValueError("Users require an email field")
        email = self.normalize_email(email)
        user = self.model(email=email, **fields)
        user.set_password(fields[self.password_field_name])
        user.save(using=self._db)
        return user

    def create_user(self, email=None, **fields):
        fields.setdefault("is_staff", False)
        fields.setdefault("is_superuser", False)
        return self._create_user(email, **fields)

    def create_superuser(self, email=None, **fields):
        fields.setdefault("is_staff", True)
        fields.setdefault("is_superuser", True)

        if fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, **fields)

    def get_by_natural_key(self, username):
        return self.get(**{self.username_field_name: username})
