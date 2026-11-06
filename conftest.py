import pytest


@pytest.fixture(autouse=True)
def _plain_static_storage(settings):
    """Tests don't run collectstatic, so skip the hashed-manifest storage."""
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
