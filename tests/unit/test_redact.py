import pytest

from mcp_server_celery.redact import mask_url, redact


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("amqp://admin:hunter2@rabbit:5672//", "amqp://admin:****@rabbit:5672//"),
        ("redis://:p%40ss@redis:6379/0", "redis://:****@redis:6379/0"),
        ("rediss://user:pw@host/1", "rediss://user:****@host/1"),
        ("redis://redis:6379/0", "redis://redis:6379/0"),
        ("amqp://guest@localhost//", "amqp://guest@localhost//"),
    ],
)
def test_mask_url(url, expected):
    assert mask_url(url) == expected


def test_redact_masks_secret_keys_and_nested_urls():
    payload = {
        "broker": {"password": "hunter2", "userid": "admin"},
        "urls": ["amqp://a:b@h//"],
        "empty_password": {"password": None},
        "count": 3,
    }

    assert redact(payload) == {
        "broker": {"password": "****", "userid": "admin"},
        "urls": ["amqp://a:****@h//"],
        "empty_password": {"password": None},
        "count": 3,
    }
