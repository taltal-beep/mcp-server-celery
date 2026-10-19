from kombu.exceptions import ChannelError

from mcp_server_celery.client import CeleryClient


class FakeChannel:
    def __init__(self, declare_result=None, error=None):
        self.declare_result, self.error = declare_result, error
        self.closed = False
        self.passive_flags = []

    def queue_declare(self, queue, passive):
        self.passive_flags.append(passive)
        if self.error:
            raise self.error
        return self.declare_result

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, channel):
        self._channel = channel

    def channel(self):
        return self._channel


def test_amqp_queue_reports_messages_and_consumers():
    channel = FakeChannel(declare_result=("emails", 9, 2))

    result = CeleryClient._probe(FakeConnection(channel), "emails", is_amqp=True)

    assert result == {"queue": "emails", "exists": True, "messages": 9, "consumers": 2}
    assert channel.passive_flags == [True]
    assert channel.closed


def test_amqp_missing_queue():
    channel = FakeChannel(error=ChannelError("NOT_FOUND"))

    result = CeleryClient._probe(FakeConnection(channel), "ghost", is_amqp=True)

    assert result == {"queue": "ghost", "exists": False, "messages": None, "consumers": None}
    assert channel.closed


def test_redis_drained_queue_is_zero():
    result = CeleryClient._probe(FakeConnection(FakeChannel(error=ChannelError("NOT_FOUND"))), "q", is_amqp=False)

    assert result == {"queue": "q", "exists": None, "messages": 0, "consumers": None}


def test_redis_consumer_count_is_unknown():
    result = CeleryClient._probe(FakeConnection(FakeChannel(declare_result=("q", 3, 0))), "q", is_amqp=False)

    assert result["consumers"] is None
    assert result["messages"] == 3
