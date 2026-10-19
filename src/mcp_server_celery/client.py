import os
import sys
from contextlib import suppress
from typing import Any, Protocol

from celery import Celery
from celery.utils.imports import symbol_by_name
from kombu.exceptions import ChannelError

from mcp_server_celery.config import DEFAULT_BROKER_URL, Settings


class Inspector(Protocol):
    def ping(self) -> dict[str, Any] | None: ...
    def stats(self) -> dict[str, Any] | None: ...
    def active_queues(self) -> dict[str, list[dict[str, Any]]] | None: ...


class CeleryClient:
    def __init__(self, app: Celery, inspect_timeout: float = 1.0):
        self.app = app
        self.inspect_timeout = inspect_timeout

    @classmethod
    def from_settings(cls, settings: Settings) -> "CeleryClient":
        if settings.app_path:
            if os.getcwd() not in sys.path:
                sys.path.insert(0, os.getcwd())  # match `celery -A`, which imports from cwd
            app = symbol_by_name(settings.app_path)
            if settings.broker_url:
                app.conf.broker_url = settings.broker_url
            if settings.result_backend:
                app.conf.result_backend = settings.result_backend
        else:
            app = Celery(
                "mcp-server-celery",
                broker=settings.broker_url or DEFAULT_BROKER_URL,
                backend=settings.result_backend,
            )
        return cls(app, settings.inspect_timeout)

    def inspect(self, timeout: float | None = None, destination: list[str] | None = None) -> Inspector:
        return self.app.control.inspect(timeout=timeout or self.inspect_timeout, destination=destination)

    def configured_queues(self) -> list[str]:
        queues = self.app.conf.task_queues or []
        names = [q.name for q in queues]
        default = self.app.conf.task_default_queue
        return names if default in names else [default, *names]

    def queue_depths(self, names: list[str]) -> list[dict[str, Any]]:
        with self.app.connection_for_read() as conn:
            conn.ensure_connection(max_retries=1)
            is_amqp = conn.transport.driver_type == "amqp"
            return [self._probe(conn, name, is_amqp) for name in names]

    @staticmethod
    def _probe(conn, name: str, is_amqp: bool) -> dict[str, Any]:
        channel = conn.channel()
        try:
            _, messages, consumers = channel.queue_declare(queue=name, passive=True)
        except ChannelError:
            if is_amqp:
                return {
                    "queue": name,
                    "exists": False,
                    "messages": None,
                    "consumers": None,
                }
            # Virtual transports drop the key once a queue is drained.
            return {"queue": name, "exists": None, "messages": 0, "consumers": None}
        finally:
            with suppress(ChannelError, OSError):
                channel.close()
        return {
            "queue": name,
            "exists": True,
            "messages": messages,
            "consumers": consumers if is_amqp else None,
        }
