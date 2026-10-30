from django import forms
from django.contrib import admin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html

from hub.models import App
from .models import User


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
    list_display = ("email", "first_name", "last_name", "app_count", "is_active", "is_staff", "last_login")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    readonly_fields = ("google_sub",)
    actions = ["bulk_grant_apps"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("App access", {"fields": ("apps",)}),
        ("Google", {"fields": ("google_sub",), "classes": ("collapse",)}),
    )

    # --- list column: number of directly granted apps ---
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _app_count=Count("granted_apps", distinct=True)
        )

    @admin.display(description="Apps", ordering="_app_count")
    def app_count(self, obj):
        count = obj._app_count
        if not count:
            return "0"
        url = reverse("admin:hub_app_changelist") + f"?allowed_users__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

    # --- save the multi-select (runs after the user and its M2Ms are saved) ---
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if "apps" in form.cleaned_data:  # absent on the "add user" form
            form.instance.granted_apps.set(form.cleaned_data["apps"])

    # --- bonus: bulk action on the user list ---
    @admin.action(description="Grant / revoke apps for selected users")
    def bulk_grant_apps(self, request, queryset):
        if "apply" in request.POST:
            form = BulkGrantForm(request.POST)
            if form.is_valid():
                apps, mode = form.cleaned_data["apps"], form.cleaned_data["mode"]
                for user in queryset:
                    if mode == BulkGrantForm.MODE_REPLACE:
                        user.granted_apps.set(apps)
                    elif mode == BulkGrantForm.MODE_REMOVE:
                        user.granted_apps.remove(*apps)
                    else:
                        user.granted_apps.add(*apps)
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
