import os
import subprocess
import sys
import time
import uuid

import pytest

from mcp_server_celery.client import CeleryClient
from mcp_server_celery.config import Settings
from mcp_server_celery.tools import list_workers, queue_depths

BROKER_URL = os.environ.get("CELERY_BROKER_URL")
WORKER_NAME = f"it-{uuid.uuid4().hex[:8]}@localhost"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not BROKER_URL, reason="CELERY_BROKER_URL not set"),
]


@pytest.fixture(scope="module")
def client():
    return CeleryClient.from_settings(Settings(broker_url=BROKER_URL, inspect_timeout=2.0))


@pytest.fixture(scope="module")
def worker(client):
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "tests.integration.worker_app",
            "worker",
            "-Q",
            "celery,emails",
            "-P",
            "solo",
            "-c",
            "1",
            "-n",
            WORKER_NAME,
            "--loglevel",
            "WARNING",
        ],
    )
    try:
        deadline = time.monotonic() + 60
        while WORKER_NAME not in (client.inspect(destination=[WORKER_NAME]).ping() or {}):
            if proc.poll() is not None or time.monotonic() > deadline:
                pytest.fail("worker did not come up")
        yield WORKER_NAME
    finally:
        proc.terminate()
        proc.wait(timeout=30)


def test_list_workers_reports_live_worker(client, worker):
    workers = {w["hostname"]: w for w in list_workers(client)["workers"]}

    live = workers[worker]
    assert live["responded_to_ping"] is True
    assert live["concurrency"] == 1
    assert live["queues"] == ["celery", "emails"]
    assert live["uptime_seconds"] >= 0


def test_queue_depths_finds_backlog_nobody_consumes(client, worker):
    orphaned = f"orphaned-{uuid.uuid4().hex[:8]}"
    for i in range(3):
        client.app.send_task("integration.add", args=(i, i), queue=orphaned)

    result = queue_depths(client, queues=["emails", orphaned])

    by_name = {q["queue"]: q for q in result["queues"]}
    assert by_name[orphaned]["messages"] == 3
    assert by_name[orphaned]["workers_consuming"] == []
    assert worker in by_name["emails"]["workers_consuming"]


def test_default_queue_list_includes_consumed_queues(client, worker):
    names = [q["queue"] for q in queue_depths(client)["queues"]]

    assert {"celery", "emails"} <= set(names)


def test_unknown_queue_does_not_raise(client, worker):
    (ghost,) = queue_depths(client, queues=[f"ghost-{uuid.uuid4().hex[:8]}"])["queues"]

    assert ghost["exists"] in (False, None)
    assert ghost["workers_consuming"] == []
