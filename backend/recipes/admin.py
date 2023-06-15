from django.contrib import admin

from recipes.models import Favorite, Ingredient, IngredientAmount, Recipe, ShoppingCart, Subscription, Tag


class IngredientAmountAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')


class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'color', 'slug')


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'text', 'cooking_time')


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')


admin.site.register(Favorite)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(IngredientAmount, IngredientAmountAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShoppingCart)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Tag, TagAdmin)
