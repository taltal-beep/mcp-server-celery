from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from kombu.exceptions import OperationalError
from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_server_celery import tools
from mcp_server_celery.client import CeleryClient
from mcp_server_celery.config import Settings
from mcp_server_celery.redact import mask_url

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=True)

Timeout = Annotated[
    float | None,
    Field(description="Seconds to wait for worker replies. Defaults to CELERY_INSPECT_TIMEOUT."),
]


def _broker_errors(client: CeleryClient, fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (OperationalError, ConnectionError, OSError) as exc:
            broker = mask_url(client.app.conf.broker_url or "")
            raise ToolError(f"Cannot reach broker {broker}: {mask_url(str(exc))}") from exc

    return wrapper


def build_server(client: CeleryClient) -> FastMCP:
    mcp = FastMCP(
        "celery",
        instructions=(
            "Read-only diagnostics for a Celery deployment: workers, queues and tasks. "
            "Broker credentials are always masked."
        ),
    )

    def _wrap(fn):
        return _broker_errors(client, fn)

    @mcp.tool(annotations=READ_ONLY)
    @_wrap
    def list_workers(timeout: Timeout = None) -> dict:
        """List workers that reply to broadcast, with pool, concurrency, uptime and the queues each consumes."""
        return tools.list_workers(client, timeout=timeout)

    @mcp.tool(annotations=READ_ONLY)
    @_wrap
    def queue_depths(
        queues: Annotated[
            list[str] | None,
            Field(
                description="Queue names to check. Defaults to configured queues plus every queue a worker consumes."
            ),
        ] = None,
        timeout: Timeout = None,
    ) -> dict:
        """Count waiting messages per queue and show which workers consume each one. Works on RabbitMQ and Redis."""
        return tools.queue_depths(client, queues=queues, timeout=timeout)

    return mcp


def main() -> None:
    build_server(CeleryClient.from_settings(Settings.from_env())).run()
