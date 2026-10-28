from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import verify_google_credential, get_or_create_user, GoogleAuthError


def login_page(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    domains = settings.GOOGLE_ALLOWED_DOMAINS
    return render(request, "accounts/login.html", {
        "google_client_id": settings.GOOGLE_CLIENT_ID,
        "login_uri": request.build_absolute_uri(reverse("accounts:google_callback")),
        "hosted_domain": domains[0] if len(domains) == 1 else "",
    })


def _complete_google_login(request, credential: str):
    """Shared by redirect and popup modes: verify token, resolve user, log in."""
    try:
        identity = verify_google_credential(credential)
    except GoogleAuthError as exc:
        messages.error(request, str(exc))
        return redirect("accounts:login")

    user = get_or_create_user(identity)
    if not user.is_active:
        messages.error(request, "Your account is disabled. Contact the administrator.")
        return redirect("accounts:login")

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect(settings.LOGIN_REDIRECT_URL)


@csrf_exempt  # redirect mode: Google posts cross-site, uses its own double-submit token
@require_POST
def google_callback(request):
    cookie_token = request.COOKIES.get("g_csrf_token")
    if not cookie_token or cookie_token != request.POST.get("g_csrf_token"):
        messages.error(request, "Sign-in failed (CSRF check). Please try again.")
        return redirect("accounts:login")
    return _complete_google_login(request, request.POST.get("credential", ""))


@require_POST  # popup mode: same-origin form, so normal Django CSRF protection applies
def google_verify(request):
    return _complete_google_login(request, request.POST.get("credential", ""))