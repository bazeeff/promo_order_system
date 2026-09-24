from django.core.management.base import BaseCommand, CommandError

from ...models import User


class Command(BaseCommand):
    help = "Создание пользователя с админскими правами"

    def handle(self, *args, **kwargs):  # noqa: WPS110
        try:  # noqa: WPS229
            user = User.objects.create(
                email="test@test.ru",
                first_name="admin",
                last_name="admin",
            )
            user.is_staff = True
            user.is_superuser = True
            user.set_password("1234")
            user.save()
            print("Создан админ +79000000/123")  # noqa: T001 WPS421
        except Exception as e:
            raise CommandError(e)
