from django.contrib import admin

from recipes.models import (
    Favorite, Ingredient, IngredientAmount, Recipe,
    ShoppingCart, Tag
)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_filter = ('name',)
    empty_value_display = '-пусто-'


class IngredientInline(admin.TabularInline):
    model = IngredientAmount


@admin.display
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'total_favorites')
    list_filter = ('author', 'name', 'tags')
    inlines = (IngredientInline,)

    def total_favorites(self, obj):
        return Favorite.objects.filter(recipe=obj).count()

    total_favorites.short_description = 'Всего в избранном'


admin.site.register(Favorite)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(IngredientAmount)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShoppingCart)
admin.site.register(Tag)
