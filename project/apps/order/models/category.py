from apps.helpers.models import UUIDModel, CreatedModel
from django.db import models


class Category(UUIDModel, CreatedModel):
    name = models.CharField(
        "Название",
        max_length=120,
        unique=True,
    )

    class Meta:
        ordering = ("id",)
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self) -> str:
        return self.name
