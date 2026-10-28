from django.contrib import admin
from .models import App


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "display_order", "user_count")
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active", "allowed_groups")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("allowed_users", "allowed_groups")

    @admin.display(description="Direct users")
    def user_count(self, obj):
        return obj.allowed_users.count()