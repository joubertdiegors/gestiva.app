from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, AccessProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'get_full_name', 'email', 'get_profile_name', 'is_active', 'date_joined')
    list_filter   = ('access_profile', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    fieldsets = UserAdmin.fieldsets + (
        (_("Perfil Construart"), {
            'fields': ('phone', 'access_profile'),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_("Perfil Construart"), {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'access_profile'),
        }),
    )


@admin.register(AccessProfile)
class AccessProfileAdmin(admin.ModelAdmin):
    list_display  = ('group', 'color', 'user_count', 'created_at')
    search_fields = ('group__name',)