from django.urls import path
from . import views

app_name = "hub"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("apps/<slug:slug>/", views.launch, name="launch"),
    path("requests/new/", views.request_access, name="request_access"),
    path("requests/<int:pk>/cancel/", views.cancel_request, name="cancel_request"),
    path("internal/auth/<slug:slug>/", views.nginx_auth, name="nginx_auth"),
]
