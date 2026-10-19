from typing import Any

import pytest
from celery import Celery

from mcp_server_celery.client import CeleryClient

STATS = {
    "worker1@host": {
        "pid": 101,
        "uptime": 3600,
        "prefetch_count": 16,
        "pool": {"implementation": "celery.concurrency.prefork:TaskPool", "max-concurrency": 4},
        "total": {"app.add": 12},
        "broker": {"hostname": "rabbit", "userid": "admin", "password": "hunter2"},
    },
    "worker2@host": {
        "pid": 202,
        "uptime": 60,
        "prefetch_count": 4,
        "pool": {"implementation": "celery.concurrency.threads:TaskPool", "max-concurrency": 1},
        "total": {},
    },
}
ACTIVE_QUEUES = {
    "worker1@host": [{"name": "celery"}, {"name": "emails"}],
    "worker2@host": [{"name": "celery"}],
}


class FakeInspector:
    def __init__(self, ping=None, stats=None, active_queues=None):
        self._ping, self._stats, self._active_queues = ping, stats, active_queues

    def ping(self):
        return self._ping

    def stats(self):
        return self._stats

    def active_queues(self):
        return self._active_queues


class FakeClient(CeleryClient):
    def __init__(self, inspector: FakeInspector, depths: dict[str, int | None] | None = None, **conf: Any):
        app = Celery("test", broker="amqp://admin:s3cret@rabbit:5672//", set_as_current=False)
        app.conf.update(conf)
        super().__init__(app)
        self.inspector = inspector
        self.depths = depths or {}
        self.inspect_calls: list[float | None] = []

    def inspect(self, timeout=None, destination=None):
        self.inspect_calls.append(timeout)
        return self.inspector

    def queue_depths(self, names):
        return [
            {"queue": n, "exists": n in self.depths, "messages": self.depths.get(n), "consumers": None} for n in names
        ]


@pytest.fixture
def healthy_inspector():
    return FakeInspector(
        ping={name: {"ok": "pong"} for name in STATS},
        stats=STATS,
        active_queues=ACTIVE_QUEUES,
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"
