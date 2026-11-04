from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.utils import timezone
from django.db.models import Exists, F, Func, IntegerField, OuterRef, Q, Subquery


# ---------------------------------------------------------------- App
class AppQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def accessible_by(self, user):
        if not user.is_authenticated or not user.is_active:
            return self.none()
        if user.is_superuser and getattr(settings, "HUB_SUPERUSER_SEES_ALL", False):
            return self.active()
        return self.active().filter(access_condition(user))

    def count_accessible_subquery(self):
        """
        Per-user count of accessible apps, for annotating a User queryset:
            User.objects.annotate(n=App.objects.count_accessible_subquery())
        """
        user_ref = OuterRef(OuterRef("pk"))  # User is two levels up: User → App → grant
        counted = (
            self.active()
            .filter(access_condition(user_ref))
            .order_by()  # drop App's default ordering inside the subquery
            .annotate(n=Func(F("pk"), function="COUNT", output_field=IntegerField()))
            .values("n")
        )
        return Subquery(counted, output_field=IntegerField())

class App(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    launch_url = models.URLField(blank=True, help_text="Leave blank to show as 'Coming soon'")
    icon_svg = models.TextField(blank=True, help_text="Inner SVG markup for a 24x24 viewBox. Admin-trusted.")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="AppGrant",
        through_fields=("app", "user"),
        blank=True,
        related_name="granted_apps",
    )
    allowed_groups = models.ManyToManyField(Group, blank=True, related_name="granted_apps")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AppQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------- AppGrant
class AppGrantQuerySet(models.QuerySet):
    def current(self, at=None):
        """Grants that have not expired."""
        at = at or timezone.now()
        return self.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=at))

    def expired(self, at=None):
        return self.filter(expires_at__lte=at or timezone.now())


class AppGrant(models.Model):
    """One user's direct access to one app."""
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="grants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="app_grants")

    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    granted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Leave blank for permanent access")
    note = models.CharField(max_length=255, blank=True)

    objects = AppGrantQuerySet.as_manager()

    class Meta:
        db_table = "hub_app_allowed_users"  # reuse the existing table
        unique_together = [("app", "user")]
        verbose_name = "app access grant"

    def __str__(self) -> str:
        return f"{self.user} → {self.app}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()


# ---------------------------------------------------------------- LaunchEvent
class LaunchEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="launches")
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="launches")
    launched_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-launched_at"]
        indexes = [
            models.Index(fields=["user", "-launched_at"], name="launch_user_recent"),
            models.Index(fields=["app", "-launched_at"], name="launch_app_recent"),
        ]

    def __str__(self) -> str:
        return f"{self.user} launched {self.app} at {self.launched_at:%Y-%m-%d %H:%M}"

# --------------------------------------------------------------- AccessRequest
class AccessRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_requests")
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="access_requests")
    reason = models.TextField(blank=True, max_length=500)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # At most ONE pending request per (user, app); old decided ones don't count
            models.UniqueConstraint(
                fields=["user", "app"],
                condition=Q(status="pending"),
                name="one_pending_request_per_user_app",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.app} ({self.get_status_display()})"


def access_condition(user_ref):
    """
    THE access rule: a current direct grant OR membership of a granted group.
    `user_ref` is a User instance, or an OuterRef when used inside a subquery.
    """
    direct = AppGrant.objects.current().filter(app=OuterRef("pk"), user=user_ref)
    via_group = App.allowed_groups.through.objects.filter(app=OuterRef("pk"), group__user=user_ref)
    return Exists(direct) | Exists(via_group)
