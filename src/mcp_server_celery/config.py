import os
from dataclasses import dataclass

DEFAULT_BROKER_URL = "amqp://guest:guest@localhost:5672//"


@dataclass(frozen=True)
class Settings:
    broker_url: str | None = None
    result_backend: str | None = None
    app_path: str | None = None
    inspect_timeout: float = 1.0

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        return cls(
            broker_url=env.get("CELERY_BROKER_URL") or None,
            result_backend=env.get("CELERY_RESULT_BACKEND") or None,
            app_path=env.get("CELERY_APP") or None,
            inspect_timeout=float(env.get("CELERY_INSPECT_TIMEOUT", "1.0")),
        )
