import pytest
from django.contrib import admin
from django.urls import reverse

from hub.models import AppGrant


@pytest.fixture
def data(app, user, admin_user):
    AppGrant.objects.create(app=app, user=user, granted_by=admin_user)


@pytest.mark.parametrize("model", list(admin.site._registry), ids=lambda m: m._meta.label)
def test_admin_pages_load(admin_client, data, model):
    opts = model._meta
    base = f"admin:{opts.app_label}_{opts.model_name}"
    assert admin_client.get(reverse(f"{base}_changelist")).status_code == 200
    # 403 is fine for admins that deliberately disallow adding (Access requests, Launch events)
    assert admin_client.get(reverse(f"{base}_add")).status_code in (200, 403)
    obj = model._default_manager.first()
    if obj is not None:
        assert admin_client.get(reverse(f"{base}_change", args=[obj.pk])).status_code == 200