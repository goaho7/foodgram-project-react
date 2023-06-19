from django.db import connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.permissions import IsAuthorAdminOrReadOnly
from api.serializers import (IngredientSerializer, RecipeSerializer,
                             TagSerializer)
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from users.serializers import RecipeUserSerializer


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ Теги """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ Ингредиенты """

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """ Рецепты """

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    http_method_names = ('get', 'post', 'patch', 'delete')
    permission_classes = (IsAuthorAdminOrReadOnly,)

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
            favorite_recipe, created = Favorite.objects.get_or_create(
                user=request.user,
                recipe=recipe
            )
            if not created:
                return Response(
                    {'error': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = RecipeUserSerializer(favorite_recipe)
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
        if not response.content:
            return Response(
                    {'error': 'Список покупок пуст'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return response
