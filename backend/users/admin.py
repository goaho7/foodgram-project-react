from django.contrib import admin

from users.models import CustomUser, Subscription


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'first_name', 'last_name', 'email')
    list_filter = ('email', 'username')
    empty_value_display = '-пусто-'


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Subscription)
