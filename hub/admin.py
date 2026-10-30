from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db.models import Count

from .models import App

USER_FILTER = "allowed_users__id__exact"


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "display_order", "user_count", "group_count")
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active", "allowed_groups")
    search_fields = ("name", "slug", "allowed_users__email")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("allowed_users", "allowed_groups")
    actions = ["unassign_from_user", "archive_apps"]

    # ---------- helpers ----------
    def _filtered_user(self, request):
        """The user this list is filtered to (via the Users list link), or None."""
        user_id = request.GET.get(USER_FILTER)
        if not user_id:
            return None
        return get_user_model().objects.filter(pk=user_id).first()

    # ---------- context-aware actions ----------
    def get_actions(self, request):
        actions = super().get_actions(request)
        if self._filtered_user(request):
            actions.pop("delete_selected", None)    # never delete apps from a user's view
            actions.pop("archive_apps", None)
        else:
            actions.pop("unassign_from_user", None)  # unassign needs a user context
        return actions

    @admin.action(description="Unassign selected apps from this user")
    def unassign_from_user(self, request, queryset):
        user = self._filtered_user(request)
        if user is None:
            self.message_user(request, "Open this list from a user's app count to unassign.", messages.WARNING)
            return
        count = queryset.count()
        user.granted_apps.remove(*queryset)
        self.message_user(
            request,
            f"Unassigned {count} app(s) from {user.email}. The apps themselves were not deleted.",
            messages.SUCCESS,
        )

    @admin.action(description="Archive selected apps (hide from everyone, keep grants)")
    def archive_apps(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Archived {updated} app(s).", messages.SUCCESS)

    # ---------- page title when filtered ----------
    def changelist_view(self, request, extra_context=None):
        user = self._filtered_user(request)
        if user:
            extra_context = {**(extra_context or {}), "title": f"Apps directly assigned to {user.email}"}
        return super().changelist_view(request, extra_context)

    # ---------- counts ----------
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _users=Count("allowed_users", distinct=True),
            _groups=Count("allowed_groups", distinct=True),
        )

    @admin.display(description="Users", ordering="_users")
    def user_count(self, obj):
        return obj._users

    @admin.display(description="Groups", ordering="_groups")
    def group_count(self, obj):
        return obj._groups
    
    def has_delete_permission(self, request, obj=None):
        return False