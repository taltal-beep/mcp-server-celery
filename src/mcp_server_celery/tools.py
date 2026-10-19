from typing import Any

from mcp_server_celery.client import CeleryClient
from mcp_server_celery.redact import redact


def list_workers(client: CeleryClient, timeout: float | None = None) -> dict[str, Any]:
    inspector = client.inspect(timeout=timeout)
    pings = inspector.ping() or {}
    stats = inspector.stats() or {}
    queues = inspector.active_queues() or {}

    workers = []
    for hostname in sorted(set(pings) | set(stats) | set(queues)):
        worker_stats = stats.get(hostname, {})
        pool = worker_stats.get("pool") or {}
        workers.append(
            {
                "hostname": hostname,
                "responded_to_ping": hostname in pings,
                "pid": worker_stats.get("pid"),
                "uptime_seconds": worker_stats.get("uptime"),
                "pool": pool.get("implementation"),
                "concurrency": pool.get("max-concurrency"),
                "prefetch_count": worker_stats.get("prefetch_count"),
                "tasks_processed": worker_stats.get("total", {}),
                "queues": sorted(q["name"] for q in queues.get(hostname, [])),
            }
        )
    return redact({"worker_count": len(workers), "workers": workers})


def queue_depths(client: CeleryClient, queues: list[str] | None = None, timeout: float | None = None) -> dict[str, Any]:
    consumed_by: dict[str, list[str]] = {}
    for hostname, worker_queues in (client.inspect(timeout=timeout).active_queues() or {}).items():
        for q in worker_queues:
            consumed_by.setdefault(q["name"], []).append(hostname)

    names = queues or sorted(set(client.configured_queues()) | set(consumed_by))
    results = []
    for depth in client.queue_depths(names):
        listeners = sorted(consumed_by.get(depth["queue"], []))
        results.append({**depth, "workers_consuming": listeners})
    return redact({"broker": client.app.conf.broker_url, "queues": results})
