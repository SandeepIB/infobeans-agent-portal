from django.contrib.auth.views import LogoutView
from django.urls import path
from accounts import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("logout/", LogoutView.as_view(next_page="accounts:login"), name="logout"),
    path("google/callback/", views.google_callback, name="google_callback"),
]