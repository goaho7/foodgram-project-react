from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.paginators import CustomPageNumberPaginator
from api.permissions import IsAuthorAdminOrReadOnly
from api.serializers import (
    AddRecipeSerializer, CustomUserSerializer,
    FavoriteSerializer, IngredientSerializer,
    RecipeSerializer, ShoppingCartSerializer,
    SubscribeUnsubscribeSerializer,
    SubscriptionsSerializer, TagSerializer
)
from recipes.models import (
    Favorite, Ingredient, IngredientAmount, Recipe,
    ShoppingCart, Tag
)
from users.models import Subscription

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ Теги """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ Ингредиенты """

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """ Рецепты """

    queryset = Recipe.objects.all()
    http_method_names = ('get', 'post', 'patch', 'delete')
    permission_classes = (IsAuthorAdminOrReadOnly,)
    pagination_class = CustomPageNumberPaginator
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        return AddRecipeSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Recipe.objects.all()
        return Recipe.objects.with_annotations(user)

    @staticmethod
    def recipe_save(serializer, pk, request):

        data = {
            'user': request.user.id,
            'recipe': pk
        }
        recipe = get_object_or_404(Recipe, id=pk)
        serializer = serializer(data=data, context={'recipe': recipe})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        methods=('post',),
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk):
        """ Добавить в избранное """

        return self.recipe_save(FavoriteSerializer, pk, request)

    @action(
        methods=('post',),
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk):
        """ Добавить в список покупок """

        return self.recipe_save(ShoppingCartSerializer, pk, request)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        """ Удалить из избранного """

        get_object_or_404(Favorite, user=request.user, recipe=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        """ Удалить из списка покупок """

        get_object_or_404(ShoppingCart, user=request.user, recipe=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def file_generation(shopping_cart):
        """ Формирование файла со списком покупок """

        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="list.txt"'
        for index, products in enumerate(shopping_cart, 1):
            name, unit, amount = products
            response.write(
                f'{index}. {products[name]}'
                f'({products[unit]}) — {products[amount]}\n'
            )
        if not response.content:
            return Response(
                {'error': 'Список покупок пуст'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return response

    @action(
        detail=False,
        methods=('get',),
        permission_classes=[IsAuthenticated, ]
    )
    def download_shopping_cart(self, request):
        """ Скачивание списка покупок """

        shopping_cart = IngredientAmount.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        return self.file_generation(shopping_cart)


class CustomUserViewSet(UserViewSet):
    """ Пользователи """

    pagination_class = PageNumberPagination

    @action(
        methods=['GET'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        """Метод обработки запросов на users/me/"""

        serializer = CustomUserSerializer(
            request.user, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=['get'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def subscriptions(self, request):
        """ Метод списка подписок """

        pages = self.paginate_queryset(
            User.objects.filter(following__user=self.request.user)
        )
        serializer = SubscriptionsSerializer(
            pages, context={'request': request}, many=True
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=('post',),
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        """ Метод подписки на автора """

        author = get_object_or_404(User, id=id)
        serializer = SubscribeUnsubscribeSerializer(
            data={'user': request.user.id, 'author': author.id},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            SubscriptionsSerializer(author, context={'request': request}).data,
            status=status.HTTP_200_OK
        )

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        """ Удалить из подписок """

        get_object_or_404(Subscription, user=request.user, author=id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
