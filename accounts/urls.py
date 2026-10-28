from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("google/verify/", views.google_verify, name="google_verify"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
