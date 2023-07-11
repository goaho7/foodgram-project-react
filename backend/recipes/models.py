from colorfield.fields import ColorField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        'Название',
        max_length=settings.MAX_LENGTH,
        unique=True
    )
    color = ColorField(
        'Цвет в HEX',
        unique=True
    )
    slug = models.SlugField(
        'Уникальный слаг',
        max_length=settings.MAX_LENGTH,
        unique=True
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=settings.MAX_LENGTH,
        db_index=True,
        verbose_name='Название',
    )
    measurement_unit = models.CharField(
        max_length=10,
        verbose_name='Единица измерения',
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_name_measurement_unit',
            ),
        )

    def __str__(self):
        return self.name


class RecipeManager(models.Manager):
    def with_annotations(self, user):
        return self.get_queryset().annotate(
            is_favorited=models.Exists(Favorite.objects.filter(
                user=models.OuterRef('author'), recipe_id=models.OuterRef('pk')
            )),
            is_in_shopping_cart=models.Exists(ShoppingCart.objects.filter(
                user=models.OuterRef('author'), recipe_id=models.OuterRef('pk')
            )),
        )


class Recipe(models.Model):
    name = models.CharField(
        verbose_name='Название',
        max_length=settings.MAX_LENGTH,
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор рецепта',
        related_name='recipes',
        on_delete=models.SET_NULL,
        null=True,
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тег',
        related_name='recipes',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингредиенты',
        related_name='recipes',
        through='recipes.IngredientAmount',
    )
    image = models.ImageField(
        verbose_name='Изображение',
        upload_to='recipe_images/',
        max_length=100000000
    )
    text = models.TextField(
        verbose_name='Описание'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[
            MinValueValidator(
                1, 'Время приготовления не может быть меньше 1 минуты'
            )
        ]
    )
    pub_date = models.DateTimeField(auto_now_add=True)
    objects = RecipeManager()

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        return self.name


class IngredientAmount(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='ingredients_in_recipe',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE,
        related_name='ingredients_in_recipe',
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=(
            MinValueValidator(
                1,
                'Количество не может быть меньше 1',
            ),
        ),
    )

    class Meta:
        verbose_name = 'Ингредиенты рецепта'
        verbose_name_plural = 'Ингредиенты рецептов'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient',
            ),
        )


class BaseListModel(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепты',
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class Favorite(BaseListModel):
    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'user', ),
                name='unique_recipe_user',
            ),
        )
        default_related_name = 'in_favorites'

    def __str__(self):
        return self.recipe.name


class ShoppingCart(BaseListModel):
    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_recipe'
            ),
        )
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shopping_cart'

    def __str__(self):
        return f'Рецепт {self.recipe} в списке у {self.user}'
