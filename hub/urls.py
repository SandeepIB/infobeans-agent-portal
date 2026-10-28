from django.urls import path
from . import views

app_name = "hub"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("apps/<slug:slug>/", views.launch, name="launch"),
]