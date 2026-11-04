from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from google.auth.transport import requests as gooogle_requests
from google.oauth2 import id_token
from django.contrib.auth.models import Group
from django.db.models import Q

from .models import SignupGroupRule  # noqa: F401  (rules are queried via the related name)



User = get_user_model()

class GoogleAuthError(Exception):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    first_name: str
    last_name: str
    picture: str
    hosted_domain: str | None


def verify_google_credential(credential: str) -> GoogleIdentity:
    try:
        id_info = id_token.verify_oauth2_token(
            credential,
            gooogle_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        raise GoogleAuthError("Invalid Google credential") from e

    if not id_info.get("email_verified"):
        raise GoogleAuthError("Google email not verified")

    hd = id_info.get("hd")
    allowed = settings.GOOGLE_ALLOWED_DOMAINS
    if allowed and hd not in allowed:
        raise GoogleAuthError("This Google account's domain is not allowed")

    return GoogleIdentity(
        sub=id_info["sub"],
        email=id_info["email"],
        first_name=id_info.get("given_name", ""),
        last_name=id_info.get("family_name", ""),
        picture=id_info.get("picture", ""),
        hosted_domain=id_info.get("hd"),
    )


@transaction.atomic
def get_or_create_user(identity: GoogleIdentity) -> User:
    # 1. Known Google identity
    user = User.objects.filter(google_sub=identity.sub).first()
    # 2. Pre-created by an admin with the same email -> link it
    if user is None:
        user = User.objects.filter(email__iexact=identity.email).first()
    # 3. Brand new user
    if user is None:
        user = User(username=identity.email, email=identity.email)
        user.set_unusable_password()

    # First Google sign-in = new user OR pre-provisioned user not yet linked
    is_first_sign_in = user.pk is None or not user.google_sub

    user.google_sub = identity.sub
    user.first_name = identity.first_name or user.first_name
    user.last_name = identity.last_name or user.last_name
    user.avatar_url = identity.picture
    user.save()

    if is_first_sign_in:
        apply_signup_groups(user)
    return user


def groups_for_email(email: str):
    domain = email.rsplit("@", 1)[-1].lower()
    # One filter() call, so both conditions apply to the SAME rule row
    return Group.objects.filter(
        Q(signup_rules__email_domain="") | Q(signup_rules__email_domain=domain),
        signup_rules__is_active=True,
    ).distinct()


def apply_signup_groups(user) -> list:
    groups = list(groups_for_email(user.email))
    if groups:
        user.groups.add(*groups)  # idempotent: existing memberships are left alone
    return groups