from mcp_server_celery.tools import list_workers

from .conftest import FakeClient, FakeInspector


def test_lists_each_worker_with_pool_and_queues(healthy_inspector):
    result = list_workers(FakeClient(healthy_inspector))

    assert result["worker_count"] == 2
    worker1, worker2 = result["workers"]
    assert worker1 == {
        "hostname": "worker1@host",
        "responded_to_ping": True,
        "pid": 101,
        "uptime_seconds": 3600,
        "pool": "celery.concurrency.prefork:TaskPool",
        "concurrency": 4,
        "prefetch_count": 16,
        "tasks_processed": {"app.add": 12},
        "queues": ["celery", "emails"],
    }
    assert worker2["concurrency"] == 1
    assert worker2["queues"] == ["celery"]


def test_never_leaks_broker_password(healthy_inspector):
    assert "hunter2" not in repr(list_workers(FakeClient(healthy_inspector)))


def test_no_workers_reply():
    result = list_workers(FakeClient(FakeInspector()))

    assert result == {"worker_count": 0, "workers": []}


def test_worker_missing_from_ping_is_flagged(healthy_inspector):
    healthy_inspector._ping = {"worker1@host": {"ok": "pong"}}

    workers = {w["hostname"]: w for w in list_workers(FakeClient(healthy_inspector))["workers"]}

    assert workers["worker1@host"]["responded_to_ping"] is True
    assert workers["worker2@host"]["responded_to_ping"] is False


def test_passes_timeout_through(healthy_inspector):
    client = FakeClient(healthy_inspector)

    list_workers(client, timeout=3.0)

    assert client.inspect_calls == [3.0]
