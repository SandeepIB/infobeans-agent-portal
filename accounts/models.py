from django.contrib.auth.models import AbstractUser, Group
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)

    def __str__(self):
        return self.email or self.username


class SignupGroupRule(models.Model):
    """On a user's first sign-in, add them to `group` if their email domain matches."""
    email_domain = models.CharField(
        max_length=253, blank=True,
        help_text="e.g. infobeans.com. Leave blank to match every user.",
    )
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="signup_rules")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["email_domain", "group__name"]
        constraints = [
            models.UniqueConstraint(fields=["email_domain", "group"], name="unique_signup_rule"),
        ]

    def save(self, *args, **kwargs):
        self.email_domain = self.email_domain.strip().lower().lstrip("@")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.email_domain or 'everyone'} → {self.group}"