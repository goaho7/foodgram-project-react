from django.contrib import admin

from users.models import CustomUser


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email')
    search_fields = ('username',)
    empty_value_display = '-пусто-'


admin.site.register(CustomUser, CustomUserAdmin)
