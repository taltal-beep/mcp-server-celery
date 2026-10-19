from kombu import Queue

from mcp_server_celery.tools import queue_depths

from .conftest import FakeClient, FakeInspector


def test_defaults_to_configured_and_consumed_queues(healthy_inspector):
    client = FakeClient(
        healthy_inspector,
        depths={"celery": 0, "emails": 5, "orphaned": 40},
        task_queues=[Queue("celery"), Queue("orphaned")],
    )

    result = queue_depths(client)

    by_name = {q["queue"]: q for q in result["queues"]}
    assert sorted(by_name) == ["celery", "emails", "orphaned"]
    assert by_name["emails"]["messages"] == 5
    assert by_name["emails"]["workers_consuming"] == ["worker1@host"]
    assert by_name["celery"]["workers_consuming"] == ["worker1@host", "worker2@host"]
    assert by_name["orphaned"]["messages"] == 40
    assert by_name["orphaned"]["workers_consuming"] == []


def test_explicit_queue_list_is_respected(healthy_inspector):
    result = queue_depths(FakeClient(healthy_inspector, depths={"emails": 2}), queues=["emails"])

    assert [q["queue"] for q in result["queues"]] == ["emails"]


def test_broker_url_is_masked(healthy_inspector):
    result = queue_depths(FakeClient(healthy_inspector))

    assert result["broker"] == "amqp://admin:****@rabbit:5672//"
    assert "s3cret" not in repr(result)


def test_works_with_no_workers():
    result = queue_depths(FakeClient(FakeInspector(), depths={"celery": 7}))

    assert result["queues"] == [
        {"queue": "celery", "exists": True, "messages": 7, "consumers": None, "workers_consuming": []}
    ]
