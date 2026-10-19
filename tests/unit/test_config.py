from mcp_server_celery.client import CeleryClient
from mcp_server_celery.config import DEFAULT_BROKER_URL, Settings


def test_from_env_defaults():
    settings = Settings.from_env({})

    assert settings == Settings(broker_url=None, result_backend=None, app_path=None, inspect_timeout=1.0)


def test_from_env_reads_all_variables():
    settings = Settings.from_env(
        {
            "CELERY_BROKER_URL": "redis://localhost:6379/0",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
            "CELERY_APP": "proj.celery:app",
            "CELERY_INSPECT_TIMEOUT": "2.5",
        }
    )

    assert settings == Settings("redis://localhost:6379/0", "redis://localhost:6379/1", "proj.celery:app", 2.5)


def test_client_without_app_uses_default_broker():
    client = CeleryClient.from_settings(Settings())

    assert client.app.conf.broker_url == DEFAULT_BROKER_URL


def test_client_loads_app_and_env_overrides_broker():
    client = CeleryClient.from_settings(
        Settings(broker_url="redis://override:6379/0", app_path="tests.unit.sample_app:app")
    )

    assert client.app.main == "sample"
    assert client.app.conf.broker_url == "redis://override:6379/0"
    assert client.configured_queues() == ["celery", "emails", "reports"]
