from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from hub.models import App
from .models import User


class AppAccessInline(admin.TabularInline):
    model = App.allowed_users.through
    extra = 1
    verbose_name = "App access"
    verbose_name_plural = "App access (direct grants)"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff", "last_login")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    inlines = [AppAccessInline]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Google", {"fields": ("google_sub",)}),
    )
    readonly_fields = ("google_sub",)