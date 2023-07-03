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

    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        max_length=254,
        unique=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('last_name', 'first_name')
        constraints = [
            models.UniqueConstraint(
                fields=['username', 'email'],
                name='unique_username_email'
            )
        ]

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """ Модель подписок """

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор на которого подписан'
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_following',
            ),
            models.CheckConstraint(
                check=~models.Q(author=models.F("user")),
                name='self_subscription',
            ),
        )
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ('author',)

    def __str__(self):
        return f'{self.user} follows {self.author}'
