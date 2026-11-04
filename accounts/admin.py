from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.forms import UserChangeForm
from django.db.models import Count, Prefetch
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from hub.models import App, AppGrant
from .models import User, SignupGroupRule
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone
from .services import apply_signup_groups


def app_choices():
    return App.objects.order_by("display_order", "name")


class UserAppsChangeForm(UserChangeForm):
    """User change form with an extra 'apps' field for direct grants."""
    apps = forms.ModelMultipleChoiceField(
        queryset=App.objects.none(),
        required=False,
        widget=FilteredSelectMultiple("apps", is_stacked=False),
        label="Apps",
        help_text="Direct grants only. Access via groups is managed on the App page.",
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["apps"].queryset = app_choices()
        if self.instance.pk:
            self.fields["apps"].initial = self.instance.granted_apps.all()


class BulkGrantForm(forms.Form):
    MODE_ADD, MODE_REPLACE, MODE_REMOVE = "add", "replace", "remove"
    apps = forms.ModelMultipleChoiceField(
        queryset=App.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    mode = forms.ChoiceField(
        choices=[
            (MODE_ADD, "Add these apps (keep existing access)"),
            (MODE_REPLACE, "Replace access with exactly these apps"),
            (MODE_REMOVE, "Remove these apps"),
        ],
        initial=MODE_ADD,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["apps"].queryset = app_choices()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAppsChangeForm
    list_display = ("email", "first_name", "last_name", "app_count", "effective_count", "is_active", "is_staff", "last_login")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    readonly_fields = ("google_sub", "effective_access")
    actions = ["bulk_grant_apps", "apply_signup_rules"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("App access", {"fields": ("apps", "effective_access")}),
        ("Google", {"fields": ("google_sub",), "classes": ("collapse",)}),
    )

    # --- list column: number of directly granted apps ---
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _app_count=Count("granted_apps", distinct=True),
            _effective=App.objects.count_accessible_subquery(),
        )

    @admin.display(description="Direct", ordering="_app_count")
    def app_count(self, obj):
        count = obj._app_count
        if not count:
            return "0"
        url = reverse("admin:hub_appgrant_changelist") + f"?user__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

    @admin.display(description="Effective", ordering="_effective")
    def effective_count(self, obj):
        if not obj.is_active:
            return "—"
        if obj.is_superuser and getattr(settings, "HUB_SUPERUSER_SEES_ALL", False):
            return "All"
        url = reverse("admin:accounts_user_change", args=[obj.pk]) + "#effective-access"
        return format_html('<a href="{}">{}</a>', url, obj._effective)

    @admin.display(description="Effective access")
    def effective_access(self, obj):
        """What this user sees on their dashboard, and why."""
        if not obj.pk:
            return "—"
        if obj.is_superuser and getattr(settings, "HUB_SUPERUSER_SEES_ALL", False):
            return "Superuser: sees every active app."

        grants = {g.app_id: g for g in AppGrant.objects.current().filter(user=obj)}
        group_ids = list(obj.groups.values_list("id", flat=True))
        apps = App.objects.accessible_by(obj).prefetch_related(
            Prefetch(
                "allowed_groups",
                queryset=Group.objects.filter(pk__in=group_ids).order_by("name"),
                to_attr="via_groups",
            )
        )

        rows = []
        for app in apps:
            sources = []
            if grant := grants.get(app.pk):
                until = f" (until {timezone.localtime(grant.expires_at):%d %b %Y})" if grant.expires_at else ""
                sources.append(f"Direct{until}")
            sources += [f"Group: {g.name}" for g in app.via_groups]
            rows.append((app.name, ", ".join(sources)))

        if not rows:
            return format_html('<span id="effective-access">No access.</span>')
        body = format_html_join("", "<tr><td>{}</td><td>{}</td></tr>", rows)
        return format_html(
            '<table id="effective-access"><thead><tr><th>App</th><th>Access via</th></tr></thead>'
            "<tbody>{}</tbody></table>",
            body,
        )

    # --- save the multi-select (runs after the user and its M2Ms are saved) ---
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if "apps" in form.cleaned_data:
            form.instance.granted_apps.set(
                form.cleaned_data["apps"],
                through_defaults={"granted_by": request.user},
            )

    @admin.action(description="Apply signup group rules to selected users")
    def apply_signup_rules(self, request, queryset):
        touched = sum(1 for user in queryset if apply_signup_groups(user))
        self.message_user(request, f"Applied rules: {touched} user(s) matched at least one rule.", messages.SUCCESS)
    
    # --- bulk action on the user list ---
    @admin.action(description="Grant / revoke apps for selected users")
    def bulk_grant_apps(self, request, queryset):
        if "apply" in request.POST:
            form = BulkGrantForm(request.POST)
            if form.is_valid():
                apps, mode = form.cleaned_data["apps"], form.cleaned_data["mode"]
                for user in queryset:
                    if mode == BulkGrantForm.MODE_REPLACE:
                        user.granted_apps.set(apps, through_defaults={"granted_by": request.user})
                    elif mode == BulkGrantForm.MODE_REMOVE:
                        user.granted_apps.remove(*apps)
                    else:
                        user.granted_apps.add(*apps, through_defaults={"granted_by": request.user})
                self.message_user(
                    request,
                    f"{mode.title()}: {apps.count()} app(s) for {queryset.count()} user(s).",
                )
                return None  # back to the user list
        else:
            form = BulkGrantForm()

        return render(request, "admin/accounts/user/bulk_grant_apps.html", {
            **self.admin_site.each_context(request),
            "title": "Grant / revoke apps",
            "opts": self.model._meta,
            "users": queryset,
            "form": form,
            "action_checkbox_name": ACTION_CHECKBOX_NAME,
        })


@admin.register(SignupGroupRule)
class SignupGroupRuleAdmin(admin.ModelAdmin):
    list_display = ("domain_label", "group", "is_active", "created_at")
    list_editable = ("is_active",)
    list_filter = ("is_active", "group")
    autocomplete_fields = ("group",)
    search_fields = ("email_domain", "group__name")

    @admin.display(description="Email domain", ordering="email_domain")
    def domain_label(self, obj):
        return obj.email_domain or "Everyone (any domain)"


class GroupForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=FilteredSelectMultiple("members", is_stacked=False),
        help_text="People in this group.",
    )
    apps = forms.ModelMultipleChoiceField(
        queryset=App.objects.none(),
        required=False,
        widget=FilteredSelectMultiple("apps", is_stacked=False),
        help_text="Everyone in this group can see these apps.",
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["members"].queryset = User.objects.filter(is_active=True).order_by("email")
        self.fields["apps"].queryset = App.objects.order_by("display_order", "name")
        if self.instance.pk:
            self.fields["members"].initial = self.instance.user_set.all()
            self.fields["apps"].initial = self.instance.granted_apps.all()


admin.site.unregister(Group)  # replace Django's default Group admin


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    form = GroupForm
    list_display = ("name", "member_count", "app_count")
    fieldsets = (
        (None, {"fields": ("name",)}),
        ("Members", {"fields": ("members",)}),
        ("Apps", {"fields": ("apps",)}),
        ("Admin-site permissions", {"fields": ("permissions",), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _members=Count("user", distinct=True),
            _apps=Count("granted_apps", distinct=True),
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.user_set.set(form.cleaned_data["members"])
        form.instance.granted_apps.set(form.cleaned_data["apps"])

    @admin.display(description="Members", ordering="_members")
    def member_count(self, obj):
        url = reverse("admin:accounts_user_changelist") + f"?groups__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, obj._members)

    @admin.display(description="Apps", ordering="_apps")
    def app_count(self, obj):
        url = reverse("admin:hub_app_changelist") + f"?allowed_groups__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, obj._apps)
