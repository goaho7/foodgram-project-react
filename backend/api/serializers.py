import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.transaction import atomic
from djoser.serializers import UserCreateSerializer, UserSerializer
# from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.shortcuts import get_object_or_404

from recipes.models import (
    Favorite, Ingredient, IngredientAmount, Recipe,
    ShoppingCart, Tag
)
from users.models import Subscription

User = get_user_model()


class RegistrationSerializer(UserCreateSerializer):
    """ Сериализатор регистрации пользователя """

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'password')


class CustomUserSerializer(UserSerializer):
    """ Сериализатор пользователя """

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed')
        model = User

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and user != obj
            and user.follower.filter(author=obj).exists()
        )


class RecipeUserSerializer(serializers.ModelSerializer):
    """ Сериализатор рецептов пользователя """

    class Meta:
        fields = ('id', 'name', 'image', 'cooking_time')
        model = Recipe
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class SubscribeUnsubscribeSerializer(serializers.ModelSerializer):
    """ Сериализатор для подписки/отписки """

    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        if data['user'] == data['author']:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя'
            )
        subscription = Subscription.objects.filter(
            user=data['user'], author=data['author']
        )
        if subscription.exists():
            raise serializers.ValidationError('Такая подписка уже есть')
        return data


class SubscriptionsSerializer(CustomUserSerializer):
    """ Сериализатор для вывода подписок """

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count'
        )
        read_only_fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_is_subscribed(self, obj):
        return True

    def get_recipes(self, obj):
        recipes_limit = (
            self.context['request'].query_params.get('recipes_limit')
        )
        recipes = obj.recipes.all()

        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]

        return RecipeUserSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class TagSerializer(serializers.ModelSerializer):
    """ Сериализатор тегов """

    class Meta:
        fields = ('id', 'name', 'color', 'slug')
        model = Tag
        read_only_fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """ Сериализатор ингредиентов """

    class Meta:
        fields = ('id', 'name', 'measurement_unit')
        model = Ingredient
        read_only_fields = ('id', 'name', 'measurement_unit')


class IngredientAmountSerializer(serializers.ModelSerializer):
    """ Сериализатор ингредиентов в рецепте """

    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    id = serializers.ReadOnlyField(source='ingredient.id')

    class Meta:
        model = IngredientAmount
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class Base64ImageField(serializers.ImageField):
    """ Класс для работы с изображениями """

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class RecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор отображения рецептов """

    tags = TagSerializer(read_only=True, many=True)
    ingredients = IngredientAmountSerializer(
        many=True,
        source='ingredients_in_recipe',
        read_only=True
    )
    author = CustomUserSerializer(read_only=True)
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)
    image = Base64ImageField(max_length=512, use_url=True)

    class Meta:
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = (
            'id', 'tags', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time'
        )
        model = Recipe


class AddIngredientSerializer(serializers.ModelSerializer):
    """ Сериализатор для добавления ингредиентов в рецепт """

    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientAmount
        fields = ('id', 'amount')


class AddRecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор добавления/обновления рецепта """

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = AddIngredientSerializer(
        many=True, source='ingredients_in_recipe'
    )
    image = Base64ImageField()
    author = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        fields = (
            'name', 'tags', 'ingredients', 'image', 'text',
            'cooking_time', 'author'
        )
        model = Recipe
        validators = [
            UniqueTogetherValidator(
                queryset=Recipe.objects.all(),
                fields=('name', 'author'),
                message='Рецепт с таким названием уже есть'
            )
        ]

    def validate_ingredients(self, value):
        """ Проверка ингредиентов """

        ingredients = [ingredient.get('id') for ingredient in value]
        if not ingredients:
            raise serializers.ValidationError('Добавьте нгредиенты')
        for id in ingredients:
            if not Ingredient.objects.filter(pk=id).exists():
                raise serializers.ValidationError(
                    f'Ингредиентa с id {id} нет'
                )
        if len(set(ingredients)) != len(ingredients):
            raise serializers.ValidationError('Ингредиенты повторяются')
        if not all([0 if amount.get('amount') < 1 else 1 for amount in value]):
            raise serializers.ValidationError('Укажите количество больше 0')

        return value

    def validate_tags(self, value):
        """ Проверка тегов """

        tags = [tag for tag in value]
        if not tags:
            raise serializers.ValidationError('Теги не добавлены')
        if len(set(tags)) != len(tags):
            raise serializers.ValidationError('Теги повторяются')

        return value

    # def to_internal_value(self, data):
    #     super().to_internal_value(data)

    #     if data.get('ingredients'):
    #         ingredients = []
    #         for ingredient in data.get('ingredients'):
    #             amount = ingredient['amount']
    #             ingredient = Ingredient.objects.get(pk=ingredient['id'])
    #             ingredients.append(
    #                 {'ingredient': ingredient, 'amount': amount}
    #             )
    #     else:
    #         ingredients = None

    #     return {
    #         'ingredients': ingredients,
    #         'tags': data.get('tags'),
    #         'image': data.get('image'),
    #         'name': data.get('name'),
    #         'text': data.get('text'),
    #         'cooking_time': data.get('cooking_time')
    #     }

    @staticmethod
    def save_ingredient_amount(ingredients, recipe):
        ingredient_objs = []
        for ingredient in ingredients:
            current_ingredient = get_object_or_404(
                Ingredient, id=ingredient.get('id')
            )
            ingredient_objs.append(IngredientAmount(
                recipe=recipe,
                ingredient=current_ingredient,
                amount=ingredient.get('amount')
            ))
        IngredientAmount.objects.bulk_create(ingredient_objs)

    @atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients_in_recipe')
        tags = validated_data.pop('tags')
        validated_data['author'] = self.context.get('request').user
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.save_ingredient_amount(ingredients, recipe)

        return recipe

    @atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')

        for key in validated_data:
            if not validated_data[key]:
                validated_data[key] = getattr(instance, key)

        if tags:
            instance.tags.set(tags)
        if ingredients:
            instance.ingredients.clear()
            self.save_ingredient_amount(ingredients, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class SmallRecipeSerializer(serializers.ModelSerializer):
    """ Кратное отображение рецепта """
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):
    """ Сериализатор избранного """

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if user.in_favorites.filter(recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в избранном')
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        return SmallRecipeSerializer(
            instance.recipe,
            context={'request': request}
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """ Сериализатор списка покупок """

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if user.shopping_cart.filter(recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в списке покупок')
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        return SmallRecipeSerializer(
            instance.recipe,
            context={'request': request}
        ).data
