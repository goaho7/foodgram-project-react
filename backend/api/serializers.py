from django.contrib.auth import get_user_model
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

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
        if user.is_anonymous or (user == obj):
            return False
        return user.follower.filter(author=obj).exists()


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
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        return True

    def get_recipes(self, obj):
        recipes = obj.recipes.all()
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
    id = serializers.ReadOnlyField(source='ingredient.id', read_only=True)

    class Meta:
        model = IngredientAmount
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class RecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор рецептов """

    tags = TagSerializer(read_only=True, many=True)
    ingredients = IngredientAmountSerializer(
        many=True,
        source='ingredients_in_recipe',
        read_only=True
    )
    author = CustomUserSerializer(read_only=True)
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')
        model = Recipe

    def validate_ingredients(self, value):
        """ Проверка уникальности ингредиентов """

        ingredients = [ingredient['ingredient'] for ingredient in value]
        if len(set(ingredients)) != len(ingredients):
            raise serializers.ValidationError('Ингредиенты повторяются')
        return value

    def validate_tags(self, value):
        """ Проверка уникальности тегов """

        tags = [tag['tags'] for tag in value]
        if len(set(tags)) != len(tags):
            raise serializers.ValidationError('Теги повторяются')
        return value

    def to_internal_value(self, data):
        if data.get('ingredients'):
            ingredients = []
            for ingredient in data.get('ingredients'):
                amount = ingredient['amount']
                ingredient = get_object_or_404(Ingredient, id=ingredient['id'])
                ingredients.append(
                    {"ingredient": ingredient, "amount": amount}
                )
        else:
            ingredients = None

        if data.get('tags'):
            tags = []
            for tag in data.get('tags'):
                tag = get_object_or_404(Tag, id=tag)
                tags.append(tag)
        else:
            tags = None

        return {
            'ingredients': ingredients,
            'tags': tags,
            'image': data.get('image'),
            'name': data.get('name'),
            'text': data.get('text'),
            'cooking_time': data.get('cooking_time')
        }

    def save_ingredient_amount(self, ingredients, recipe):
        ingredient_objs = []
        for ingredient in ingredients:
            ingredient_objs.append(IngredientAmount(
                recipe=recipe,
                ingredient=ingredient['ingredient'],
                amount=ingredient['amount']
            ))
        IngredientAmount.objects.bulk_create(ingredient_objs)

    @atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.save_ingredient_amount(ingredients, recipe)
        return recipe

    @atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        for key, value in validated_data.items():
            if validated_data[key]:
                setattr(instance, key, value)
        if tags:
            instance.tags.set(tags)
        if ingredients:
            instance.ingredients.clear()
            self.save_ingredient_amount(ingredients, instance)
        return super().update(instance, validated_data)


class FavoriteSerializer(serializers.ModelSerializer):
    """ Сериализатор избранного """

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в избранном')
        return data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """ Сериализатор списка покупок """

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в списке покупок')
        return data
