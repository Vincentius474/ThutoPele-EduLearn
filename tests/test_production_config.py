from app.core.config import settings, get_cors_origins


def test_production_settings_are_configurable():
    assert isinstance(settings.BASE_URL, str)
    assert isinstance(settings.BACKEND_CORS_ORIGINS, str)
    assert isinstance(get_cors_origins(), list)
    assert settings.MAINTENANCE_MODE is False or isinstance(settings.MAINTENANCE_MODE, bool)
    assert hasattr(settings, 'ENVIRONMENT')
    assert hasattr(settings, 'DEBUG')
