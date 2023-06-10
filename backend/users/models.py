from django.contrib.auth.models import AbstractUser
from django.db import models

from users.validators import username_validator


class CustomUser(AbstractUser):
    """Кастомный пользователь"""

    username = models.CharField(
        max_length=150,
        verbose_name='Уникальный юзернейм',
        unique=True,
        validators=[username_validator],
    )

    first_name = models.CharField(
        verbose_name='Имя',
        max_length=150,
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=150,
    )
    password = models.CharField(
        verbose_name='Пароль',
        max_length=150,
    )
    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        max_length=254,
        unique=True,
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('id',)
        constraints = [
            models.UniqueConstraint(
                fields=['username', 'email'],
                name='unique_username_email'
            )
        ]

    def __str__(self):
        return self.username
