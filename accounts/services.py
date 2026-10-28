from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from google.auth.transport import requests as gooogle_requests
from google.oauth2 import id_token


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

    if not info.get("email_verified"):
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
    user = User.objects.filter(google_sub=identity.sub).first()
    if not user:
        user = User.objects.filter(email__iexact=identity.email).first()
    if user is None:
        user = User(username=identity.email, email=identity.email)
        user.set_unusable_password()

    user.google_sub = identity.sub
    user.first_name = identity.first_name or user.first_name
    user.last_name = identity.last_name or user.last_name
    user.save()
    return user