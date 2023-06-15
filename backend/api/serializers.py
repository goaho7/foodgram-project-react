from rest_framework import serializers
from recipes.models import Tag, Recipe, Ingredient, IngredientAmount, Subscription, Favorite, ShoppingCart
from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer, UserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from django.shortcuts import get_object_or_404
from django.db.transaction import atomic

User = get_user_model()


class RegistrationSerializer(UserCreateSerializer):
    """ Сериализатор регистрации """

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
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=request.user, author=obj).exists()


class TagSerializer(serializers.ModelSerializer):
    """ Сериализатор тегов """

    class Meta:
        fields = ('id', 'name', 'color', 'slug')
        model = Tag


class IngredientSerializer(serializers.ModelSerializer):
    """ Сериализатор ингредиентов """

    class Meta:
        fields = ('id', 'name', 'measurement_unit')
        model = Ingredient


class RecipeUserSerializer(serializers.ModelSerializer):
    """ Сериализатор рецептов пользователя """

    class Meta:
        fields = ('id', 'name', 'image', 'cooking_time')
        model = Recipe


class SubscriptionSerializer(CustomUserSerializer):
    """ Сериализатор подписок """

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')

    def get_recipes(self, obj):
        recipes = obj.recipes.all()
        return RecipeUserSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class IngredientAmountSerializer(serializers.ModelSerializer):
    """ Сериализатор ингредиентов в рецепте """

    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    id = serializers.ReadOnlyField(source='ingredient.id')

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
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')
        model = Recipe

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj).exists()

    def to_internal_value(self, data):
        if data.get('ingredients'):
            ingredients = []
            for ingredient in data.get('ingredients'):
                amount = ingredient['amount']
                ingredient = get_object_or_404(Ingredient, id=ingredient['id'])
                ingredients.append({"ingredient": ingredient, "amount": amount})
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
        for ingredient in ingredients:
            IngredientAmount(
                recipe=recipe,
                ingredient=ingredient["ingredient"],
                amount=ingredient["amount"]
            ).save()

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
        return instance
