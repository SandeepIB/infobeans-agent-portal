import pytest
from django.contrib.auth.models import Group

from accounts.models import SignupGroupRule
from accounts.services import GoogleIdentity, get_or_create_user


def identity(email, sub=None):
    return GoogleIdentity(sub=sub or f"sub-{email}", email=email, first_name="",
                          last_name="", picture="", hosted_domain=None)


@pytest.fixture
def staff(db):
    group = Group.objects.create(name="All staff")
    SignupGroupRule.objects.create(email_domain="InfoBeans.com", group=group)  # normalised on save
    return group


def test_new_user_gets_domain_group(staff):
    user = get_or_create_user(identity("a@infobeans.com"))
    assert user.groups.filter(pk=staff.pk).exists()


def test_other_domain_not_added(staff):
    user = get_or_create_user(identity("a@gmail.com"))
    assert not user.groups.exists()


def test_blank_domain_matches_everyone(db):
    everyone = Group.objects.create(name="Everyone")
    SignupGroupRule.objects.create(email_domain="", group=everyone)
    user = get_or_create_user(identity("x@gmail.com"))
    assert user.groups.filter(pk=everyone.pk).exists()


def test_inactive_rule_ignored(staff):
    SignupGroupRule.objects.update(is_active=False)
    user = get_or_create_user(identity("a@infobeans.com"))
    assert not user.groups.exists()


def test_preprovisioned_user_gets_groups_on_first_sign_in(staff, django_user_model):
    django_user_model.objects.create(username="p@infobeans.com", email="p@infobeans.com")
    user = get_or_create_user(identity("p@infobeans.com"))
    assert user.groups.filter(pk=staff.pk).exists()


def test_rules_not_reapplied_on_later_sign_ins(staff):
    user = get_or_create_user(identity("a@infobeans.com"))
    user.groups.remove(staff)                       # admin removes them
    get_or_create_user(identity("a@infobeans.com")) # second sign-in
    assert not user.groups.filter(pk=staff.pk).exists()