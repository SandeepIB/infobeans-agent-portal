import pytest
from hub.models import App


@pytest.fixture
def app(db):
    return App.objects.create(name="Shared", slug="shared", launch_url="https://x.test")


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create(username="u@x.com", email="u@x.com")


@pytest.fixture
def superuser(django_user_model):
    return django_user_model.objects.create_superuser("su@x.com", "su@x.com", "pw")