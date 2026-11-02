from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.db.models import Case, Count, IntegerField, Value, When
from django.urls import reverse
from django.utils.html import format_html

from . import services
from .models import AccessRequest, App, AppGrant, LaunchEvent

User = get_user_model()
USER_FILTER = "allowed_users__id__exact"

STATUS_COLOURS = {"pending": "#b26a00", "approved": "#2e7d32", "rejected": "#aa142d", "cancelled": "#676775"}


# ================================================================ App
class AppAdminForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=FilteredSelectMultiple("users", is_stacked=False),
        label="Allowed users",
        help_text="Direct grants. Set expiry dates in 'App access grants'.",
    )

    class Meta:
        model = App
        fields = ["name", "slug", "description", "launch_url", "icon_svg",
                  "display_order", "is_active", "allowed_groups"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["users"].queryset = User.objects.filter(is_active=True).order_by("email")
        if self.instance.pk:
            self.fields["users"].initial = self.instance.allowed_users.all()


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    form = AppAdminForm
    list_display = ("name", "slug", "is_active", "display_order", "user_count", "group_count")
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active", "allowed_groups")
    search_fields = ("name", "slug", "allowed_users__email")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("allowed_groups",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "launch_url", "icon_svg", "display_order", "is_active")}),
        ("Access", {"fields": ("users", "allowed_groups")}),
    )
    actions = ["unassign_from_user"]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.allowed_users.set(
            form.cleaned_data["users"],
            through_defaults={"granted_by": request.user},
        )

    # ---- user-filtered view: revoke only, never delete ----
    def _filtered_user(self, request):
        user_id = request.GET.get(USER_FILTER)
        return User.objects.filter(pk=user_id).first() if user_id else None

    def get_actions(self, request, *args, **kwargs):
        actions = super().get_actions(request, *args, **kwargs)
        actions.pop("delete_selected", None)
        if not self._filtered_user(request):
            actions.pop("unassign_from_user", None)
        return actions

    def has_delete_permission(self, request, obj=None):
        return False  # shared apps are retired via is_active, never deleted here

    @admin.action(description="Unassign selected apps from this user")
    def unassign_from_user(self, request, queryset):
        user = self._filtered_user(request)
        if user is None:
            return
        count = queryset.count()
        user.granted_apps.remove(*queryset)
        self.message_user(request, f"Unassigned {count} app(s) from {user.email}.", messages.SUCCESS)

    def changelist_view(self, request, extra_context=None):
        user = self._filtered_user(request)
        if user:
            extra_context = {**(extra_context or {}), "title": f"Apps directly assigned to {user.email}"}
        return super().changelist_view(request, extra_context)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _users=Count("allowed_users", distinct=True),
            _groups=Count("allowed_groups", distinct=True),
        )

    @admin.display(description="Users", ordering="_users")
    def user_count(self, obj):
        count = obj._users
        if not count:
            return "0"
        url = reverse("admin:hub_appgrant_changelist") + f"?app__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

    @admin.display(description="Groups", ordering="_groups")
    def group_count(self, obj):
        return obj._groups


# ================================================================ AppGrant
class ExpiryStatusFilter(admin.SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [("current", "Current"), ("expired", "Expired"), ("temporary", "Has expiry date")]

    def queryset(self, request, queryset):
        if self.value() == "current":
            return queryset.current()
        if self.value() == "expired":
            return queryset.expired()
        if self.value() == "temporary":
            return queryset.filter(expires_at__isnull=False)
        return queryset


@admin.register(AppGrant)
class AppGrantAdmin(admin.ModelAdmin):
    list_display = ("user", "app", "is_current", "expires_at", "granted_by", "granted_at")
    list_editable = ("expires_at",)
    list_filter = (ExpiryStatusFilter, "app")
    list_select_related = ("user", "app", "granted_by")
    search_fields = ("user__email", "app__name")
    autocomplete_fields = ("user", "app")
    readonly_fields = ("granted_by", "granted_at")
    date_hierarchy = "granted_at"
    fields = ("user", "app", "expires_at", "note", "granted_by", "granted_at")

    @admin.display(boolean=True, description="Current")
    def is_current(self, obj):
        return not obj.is_expired

    def save_model(self, request, obj, form, change):
        if not change:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        title = None
        if user_id := request.GET.get("user__id__exact"):
            user = User.objects.filter(pk=user_id).only("email").first()
            if user:
                title = f"App access for {user.email}"
        elif app_id := request.GET.get("app__id__exact"):
            app = App.objects.filter(pk=app_id).only("name").first()
            if app:
                title = f"Users with access to {app.name}"

        if title:
            extra_context = {**(extra_context or {}), "title": title}
        return super().changelist_view(request, extra_context)

# ================================================================ LaunchEvent (Part B)
@admin.register(LaunchEvent)
class LaunchEventAdmin(admin.ModelAdmin):
    list_display = ("launched_at", "user", "app")
    list_filter = ("app",)
    list_select_related = ("user", "app")
    search_fields = ("user__email", "app__name")
    date_hierarchy = "launched_at"

    # An audit log: readable, never editable
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

# ================================================================ AccessRequest
@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "app", "status_badge", "created_at", "short_reason", "decided_by", "decided_at")
    list_filter = ("status", "app")
    list_select_related = ("user", "app", "decided_by")
    search_fields = ("user__email", "app__name", "reason")
    date_hierarchy = "created_at"
    readonly_fields = ("user", "app", "reason", "status", "created_at", "decided_by", "decided_at")
    fields = ("user", "app", "reason", "status", "created_at", "decided_by", "decided_at", "decision_note")
    actions = ["approve_selected", "reject_selected"]

    # Requests come from users and are kept as an audit trail
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_ordering(self, request):
        pending_first = Case(
            When(status=AccessRequest.Status.PENDING, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
        return [pending_first.asc(), "-created_at"]

    def changelist_view(self, request, extra_context=None):
        pending = AccessRequest.objects.filter(status=AccessRequest.Status.PENDING).count()
        extra_context = {**(extra_context or {}), "title": f"Access requests ({pending} pending)"}
        return super().changelist_view(request, extra_context)

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        return format_html(
            '<b style="color:{}">{}</b>',
            STATUS_COLOURS.get(obj.status, "inherit"), obj.get_status_display(),
        )

    @admin.display(description="Reason")
    def short_reason(self, obj):
        return (obj.reason[:60] + "…") if len(obj.reason) > 60 else obj.reason

    @admin.action(description="Approve selected requests (grant access)")
    def approve_selected(self, request, queryset):
        total = queryset.count()
        done = sum(services.approve_request(r, by=request.user) for r in queryset)
        self.message_user(request, f"Approved {done} request(s).", messages.SUCCESS)
        if total - done:
            self.message_user(request, f"Skipped {total - done} that were not pending.", messages.WARNING)

    @admin.action(description="Reject selected requests")
    def reject_selected(self, request, queryset):
        total = queryset.count()
        done = sum(services.reject_request(r, by=request.user) for r in queryset)
        self.message_user(request, f"Rejected {done} request(s).", messages.SUCCESS)
        if total - done:
            self.message_user(request, f"Skipped {total - done} that were not pending.", messages.WARNING)
