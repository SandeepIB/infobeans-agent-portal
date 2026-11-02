import pytest
from django.contrib.auth.models import Group
from hub.models import AccessRequest, App, AppGrant
from django.urls import reverse
from hub import services

PENDING = AccessRequest.Status.PENDING


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


@pytest.mark.django_db
def test_unassign_revokes_only_for_that_user(admin_client, django_user_model):
    app = App.objects.create(name="Shared", slug="shared", launch_url="https://x.test")
    alice = django_user_model.objects.create(username="alice@x.com", email="alice@x.com")
    bob = django_user_model.objects.create(username="bob@x.com", email="bob@x.com")
    app.allowed_users.add(alice, bob)

    url = reverse("admin:hub_app_changelist") + f"?allowed_users__id__exact={alice.pk}"
    admin_client.post(url, {"action": "unassign_from_user", "_selected_action": [app.pk]})

    app.refresh_from_db()
    assert app.is_active                                   # app untouched
    assert App.objects.filter(pk=app.pk).exists()          # not deleted
    assert not app.allowed_users.filter(pk=alice.pk).exists()  # alice revoked
    assert app.allowed_users.filter(pk=bob.pk).exists()        # bob unaffected

def test_app_user_count_links_to_its_users(admin_client, app, user, django_user_model):
    other = django_user_model.objects.create(username="o@x.com", email="o@x.com")
    AppGrant.objects.create(app=app, user=user) # has access
    # 'other' has no grant

    # The Apps list shows the count as a link to the filtered grant list
    apps_page = admin_client.get(reverse("admin:hub_app_changelist"))
    assert f"?app__id__exact={app.pk}" in apps_page.content.decode()

    # The filtered grant list shows exactly this app's users
    url = reverse("admin:hub_appgrant_changelist") + f"?app__id__exact={app.pk}"
    page = admin_client.get(url).content.decode()
    assert f"Users with access to {app.name}" in page
    assert user.email in page
    assert other.email not in page

def test_user_can_request_and_admin_approves(client, app, user, admin_user):
    client.force_login(user)
    client.post(reverse("hub:request_access"), {"app": app.pk, "reason": "Need it for a proposal"})

    req = AccessRequest.objects.get(user=user, app=app)
    assert req.status == PENDING
    assert not App.objects.accessible_by(user).exists()

    assert services.approve_request(req, by=admin_user)
    req.refresh_from_db()
    assert req.status == AccessRequest.Status.APPROVED
    assert AppGrant.objects.get(user=user, app=app).granted_by == admin_user
    assert list(App.objects.accessible_by(user)) == [app]


def test_duplicate_pending_request_blocked(client, app, user):
    client.force_login(user)
    url = reverse("hub:request_access")
    client.post(url, {"app": app.pk})
    client.post(url, {"app": app.pk})
    assert AccessRequest.objects.filter(user=user, app=app).count() == 1


def test_cannot_request_app_already_accessible(app, user):
    AppGrant.objects.create(app=app, user=user)
    assert not services.requestable_apps(user).filter(pk=app.pk).exists()


def test_reject_does_not_grant(app, user, admin_user):
    req = AccessRequest.objects.create(user=user, app=app)
    assert services.reject_request(req, by=admin_user)
    assert not App.objects.accessible_by(user).exists()


def test_user_can_withdraw(client, app, user):
    req = AccessRequest.objects.create(user=user, app=app)
    client.force_login(user)
    client.post(reverse("hub:cancel_request", args=[req.pk]))
    req.refresh_from_db()
    assert req.status == AccessRequest.Status.CANCELLED


def test_admin_bulk_approve_action(admin_client, app, user):
    req = AccessRequest.objects.create(user=user, app=app)
    admin_client.post(
        reverse("admin:hub_accessrequest_changelist"),
        {"action": "approve_selected", "_selected_action": [req.pk]},
    )
    assert AppGrant.objects.filter(app=app, user=user).exists()