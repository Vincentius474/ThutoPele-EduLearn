import os

from app.core.config import settings


def test_production_settings_are_configurable():
    assert isinstance(settings.BASE_URL, str)
    assert isinstance(settings.BACKEND_CORS_ORIGINS, list)
    assert settings.MAINTENANCE_MODE is False or isinstance(settings.MAINTENANCE_MODE, bool)
    assert hasattr(settings, 'ENVIRONMENT')
    assert hasattr(settings, 'DEBUG')
