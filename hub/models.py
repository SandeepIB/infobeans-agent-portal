from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Q


class AppQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def accessible_by(self, user):
        if not user.is_authenticated:
            return self.none()
        if user.is_superuser:
            return self.active()
        return (
            self.active()
            .filter(Q(allowed_users=user) | Q(allowed_groups__in=user.groups.all()))
            .distinct()
        )


class App(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    launch_url = models.URLField(help_text="Where the app lives")
    icon = models.CharField(max_length=8, blank=True, help_text="Emoji, e.g. 🤖")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="granted_apps"
    )
    allowed_groups = models.ManyToManyField(
        Group, blank=True, related_name="granted_apps"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AppQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return self.name

    def is_accessible_by(self, user) -> bool:
        return App.objects.accessible_by(user).filter(pk=self.pk).exists()