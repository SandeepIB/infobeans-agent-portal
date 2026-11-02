from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from hub.models import App, AppGrant, LaunchEvent
from hub.tests.conftest import app, user


def test_permanent_grant_is_visible(app, user):
    AppGrant.objects.create(app=app, user=user)
    assert list(App.objects.accessible_by(user)) == [app]


def test_future_expiry_is_visible(app, user):
    AppGrant.objects.create(app=app, user=user, expires_at=timezone.now() + timedelta(days=1))
    assert App.objects.accessible_by(user).exists()


def test_expired_grant_is_hidden(app, user):
    AppGrant.objects.create(app=app, user=user, expires_at=timezone.now() - timedelta(minutes=1))
    assert not App.objects.accessible_by(user).exists()


def test_through_defaults_records_granter(app, user, django_user_model):
    admin_user = django_user_model.objects.create(username="a@x.com", email="a@x.com")
    user.granted_apps.add(app, through_defaults={"granted_by": admin_user})
    assert AppGrant.objects.get(app=app, user=user).granted_by == admin_user


def test_launch_logs_event(client, app, user):
    AppGrant.objects.create(app=app, user=user)
    client.force_login(user)
    resp = client.get(reverse("hub:launch", args=[app.slug]))
    assert resp.status_code == 302
    assert LaunchEvent.objects.filter(user=user, app=app).count() == 1


def test_denied_launch_not_logged(client, app, user):
    client.force_login(user)  # no grant
    resp = client.get(reverse("hub:launch", args=[app.slug]))
    assert resp.status_code == 404
    assert not LaunchEvent.objects.exists()


def test_expired_grant_cannot_launch(client, app, user):
    AppGrant.objects.create(app=app, user=user, expires_at=timezone.now() - timedelta(seconds=1))
    client.force_login(user)
    assert client.get(reverse("hub:launch", args=[app.slug])).status_code == 404

def test_superuser_uses_real_settings(superuser, app):
    # No override_settings: exercises whatever settings.py actually says
    assert not App.objects.accessible_by(superuser).exists()