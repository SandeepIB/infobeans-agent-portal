from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import App


@login_required
def dashboard(request):
    apps = App.objects.accessible_by(request.user)
    return render(request, "hub/dashboard.html", {"apps": apps})


@login_required
def launch(request, slug):
    app = get_object_or_404(App, slug=slug, is_active=True)
    if not app.is_accessible_by(request.user):
        raise Http404  # don't reveal that the app exists
    return redirect(app.launch_url)