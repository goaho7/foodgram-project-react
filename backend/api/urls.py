from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (
    CustomUserViewSet, IngredientViewSet, RecipeViewSet,
    TagViewSet
)

app_name = 'api'

router_v1 = DefaultRouter()

router_v1.register(r'tags', TagViewSet, basename='tags')
router_v1.register(r'recipes', RecipeViewSet, basename='recipes')
router_v1.register(r'ingredients', IngredientViewSet, basename='ingredients')
router_v1.register(r'users', CustomUserViewSet, basename='users')


auth_urls = [
    path('', include('djoser.urls')),
    path('', include('djoser.urls.authtoken')),
]

urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/', include(auth_urls)),
]
