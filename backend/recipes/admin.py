from django.contrib import admin

from recipes.models import Favorites, Ingredient, IngredientAmount, Recipe, ShoppingCart, Subscription, Tag

admin.site.register(Favorites)
admin.site.register(Ingredient)
admin.site.register(IngredientAmount)
admin.site.register(Recipe)
admin.site.register(ShoppingCart)
admin.site.register(Subscription)
admin.site.register(Tag)
