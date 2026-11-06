from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_GET

from . import services
from .forms import AccessRequestForm
from .models import AccessRequest, App, LaunchEvent
from urllib.parse import quote
from django.http import HttpResponse



DASHBOARD_FIELDS = ("name", "slug", "description", "launch_url", "icon_svg", "display_order")



@login_required
def dashboard(request):
    apps = App.objects.accessible_by(request.user).only(*DASHBOARD_FIELDS)
    request_form = AccessRequestForm(user=request.user)
    pending = (
        AccessRequest.objects.filter(user=request.user, status=AccessRequest.Status.PENDING)
        .select_related("app")
    )
    return render(request, "hub/dashboard.html", {
        "apps": apps,
        "request_form": request_form,
        "can_request": request_form.fields["app"].queryset.exists(),
        "pending_requests": pending,
    })

@login_required
def launch(request, slug):
    app = (
        App.objects.accessible_by(request.user)
        .filter(slug=slug)
        .only("id", "launch_url")
        .first()
    )
    if app is None or not app.launch_url:
        raise Http404
    LaunchEvent.objects.create(user=request.user, app=app)
    return redirect(app.launch_url)


@login_required
@require_POST
def request_access(request):
    form = AccessRequestForm(request.POST, user=request.user)
    if not form.is_valid():
        messages.error(request, "Please pick an agent you don't already have or haven't requested.")
        return redirect("hub:dashboard")
    try:
        req = services.create_request(request.user, form.cleaned_data["app"], form.cleaned_data["reason"])
    except services.AccessRequestError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Request sent for {req.app.name}. An administrator will review it.")
    return redirect("hub:dashboard")


@login_required
@require_POST
def cancel_request(request, pk):
    if services.cancel_request(request.user, pk):
        messages.info(request, "Request withdrawn.")
    return redirect("hub:dashboard")


@require_GET
def nginx_auth(request, slug):
    """Called by nginx (auth_request) before proxying to an internal app."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if not App.objects.accessible_by(request.user).filter(slug=slug).exists():
        return HttpResponse(status=403)

    resp = HttpResponse(status=200)
    resp["X-Auth-User-Id"] = str(request.user.pk)
    resp["X-Auth-Email"] = request.user.email
    resp["X-Auth-Name"] = quote(request.user.get_full_name() or request.user.email)  # header-safe
    resp["Cache-Control"] = "no-store"
    return resp