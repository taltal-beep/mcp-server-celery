import pytest
from fastmcp import Client
from kombu.exceptions import OperationalError

from mcp_server_celery.server import build_server

from .conftest import FakeClient

pytestmark = pytest.mark.anyio


async def test_tools_are_registered_read_only(healthy_inspector):
    async with Client(build_server(FakeClient(healthy_inspector))) as mcp:
        tools = {t.name: t for t in await mcp.list_tools()}

    assert set(tools) == {"list_workers", "queue_depths"}
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert all(t.annotations.destructive_hint is False for t in tools.values())


async def test_call_list_workers_over_mcp(healthy_inspector):
    async with Client(build_server(FakeClient(healthy_inspector))) as mcp:
        result = await mcp.call_tool("list_workers", {"timeout": 0.5})

    assert result.structured_content["worker_count"] == 2


async def test_call_queue_depths_over_mcp(healthy_inspector):
    client = FakeClient(healthy_inspector, depths={"emails": 3})
    async with Client(build_server(client)) as mcp:
        result = await mcp.call_tool("queue_depths", {"queues": ["emails"]})

    assert result.structured_content["queues"][0]["messages"] == 3


async def test_unreachable_broker_returns_masked_error(healthy_inspector):
    client = FakeClient(healthy_inspector)

    def refuse(names):
        raise OperationalError("Error 61 connecting to amqp://admin:s3cret@rabbit:5672//")

    client.queue_depths = refuse
    async with Client(build_server(client)) as mcp:
        result = await mcp.call_tool("queue_depths", {}, raise_on_error=False)

    message = result.content[0].text
    assert result.is_error
    assert "Cannot reach broker amqp://admin:****@rabbit:5672//" in message
    assert "s3cret" not in message
