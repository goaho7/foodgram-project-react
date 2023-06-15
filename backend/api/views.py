from rest_framework import viewsets
from recipes.models import Tag, Recipe, Ingredient, IngredientAmount, Subscription, Favorite, ShoppingCart
from api.serializers import TagSerializer, RecipeSerializer, IngredientSerializer, SubscriptionSerializer, CustomUserSerializer, RecipeUserSerializer
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from djoser.views import UserViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db import connection
import csv

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """ Пользователи """

    @action(
        methods=['GET'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        """Метод обработки запросов на users/me/"""

        serializer = CustomUserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=['get'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def subscriptions(self, request):
        """ Метод подписок """

        follower = request.user.follower.all()
        queryset = [get_object_or_404(User, username=user.author) for user in follower] # оптимизировать
        serializer = SubscriptionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        """ Метод подписки/отписки на автора """

        author = get_object_or_404(User, id=id)
        if request.method == 'POST':
            Subscription.objects.create(user=request.user, author=author)
            serializer = SubscriptionSerializer(author)
            return Response(serializer.data, status=status.HTTP_200_OK)
        Subscription.objects.filter(user=request.user, author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ Теги """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ Ингредиенты """

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    """ Рецепты """

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk):
        """ Добавить/удалить в избранное """

        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeUserSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_200_OK)
        Favorite.objects.filter(user=request.user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk):
        """ Добавить/удалить в список покупок """

        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeUserSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_200_OK)
        ShoppingCart.objects.filter(user=request.user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated, ]
    )
    def download_shopping_cart(self, request):
        """ Скачивание списка покупок """

        with connection.cursor() as cursor:
            cursor.execute(
                '''
                    SELECT recipes_ingredient.name,
                           recipes_ingredient.measurement_unit,
                           SUM(recipes_ingredientamount.amount)
                    FROM recipes_shoppingcart
                    INNER JOIN recipes_recipe
                        ON recipes_shoppingcart.recipe_id = recipes_recipe.id
                    INNER JOIN recipes_ingredientamount
                        ON (
                           recipes_ingredientamount.recipe_id
                           = recipes_recipe.id
                        )
                    INNER JOIN recipes_ingredient
                        ON (
                           recipes_ingredientamount.ingredient_id
                           = recipes_ingredient.id
                        )
                    WHERE recipes_shoppingcart.user_id = %s
                    GROUP BY recipes_ingredient.name
                ''', (request.user.id,)
            )
            shopping_cart = cursor.fetchall()
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="list.txt"'
        for index, products in enumerate(shopping_cart, 1):
            name, unit, amount = products
            response.write(f'{index}. {name} ({unit}) — {amount}\n')
        return response
