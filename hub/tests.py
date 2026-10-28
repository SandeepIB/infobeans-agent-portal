import pytest
from django.contrib.auth.models import Group
from hub.models import App


@pytest.fixture
def app(db):
    return App.objects.create(name="CRM Agent", slug="crm", launch_url="https://x.test")


def test_no_grant_no_access(django_user_model, app):
    u = django_user_model.objects.create(username="a@x.com", email="a@x.com")
    assert not App.objects.accessible_by(u).exists()


def test_direct_grant(django_user_model, app):
    u = django_user_model.objects.create(username="b@x.com", email="b@x.com")
    app.allowed_users.add(u)
    assert list(App.objects.accessible_by(u)) == [app]


def test_group_grant_no_duplicates(django_user_model, app):
    u = django_user_model.objects.create(username="c@x.com", email="c@x.com")
    g = Group.objects.create(name="Sales")
    u.groups.add(g)
    app.allowed_groups.add(g)
    app.allowed_users.add(u)  # granted both ways
    assert list(App.objects.accessible_by(u)) == [app]


def test_inactive_app_hidden(django_user_model, app):
    u = django_user_model.objects.create(username="d@x.com", email="d@x.com")
    app.allowed_users.add(u)
    app.is_active = False
    app.save()
    assert not App.objects.accessible_by(u).exists()