# mcp-server-celery

<!-- mcp-name: io.github.taltal-beep/mcp-server-celery -->

[![PyPI](https://img.shields.io/pypi/v/mcp-server-celery)](https://pypi.org/project/mcp-server-celery/)
[![CI](https://github.com/taltal-beep/mcp-server-celery/actions/workflows/ci.yml/badge.svg)](https://github.com/taltal-beep/mcp-server-celery/actions/workflows/ci.yml)

An MCP server that lets AI agents debug a running Celery deployment. It checks which workers are alive, what each one consumes, and where messages are piling up — the checks you'd otherwise run by hand with `celery inspect` and `rabbitmqctl` every time something gets stuck.

It is **read-only by default**. Broker passwords are masked in every response, including the broker info that Celery's own `inspect stats` sends back in plain text.

Works with RabbitMQ (`amqp://`) and Redis (`redis://`, `rediss://`).

## Tools

| Tool | What it answers |
| --- | --- |
| `list_workers` | Which workers respond, their pool and concurrency, uptime, prefetch count, tasks processed, and the queues each one listens to. |
| `queue_depths` | How many messages are waiting in each queue and which workers consume it. With no arguments it checks your configured queues plus every queue a live worker consumes. |

Coming next: `active_tasks`, `reserved_tasks`, `scheduled_tasks`, `task_status`, and `diagnose_stuck`, which cross-references the above to flag queues no worker listens to, tasks routed to queues with no consumer, and workers that stopped responding. See the [roadmap](#roadmap).

## Install

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uvx mcp-server-celery
```

## Configuration

All configuration is through environment variables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `CELERY_BROKER_URL` | `amqp://guest:guest@localhost:5672//` | Broker to inspect. |
| `CELERY_RESULT_BACKEND` | — | Result backend (used by `task_status`, coming in the next release). |
| `CELERY_APP` | — | Import path of your app, e.g. `proj.celery:app`. Lets the server see your `task_queues` and routes. `CELERY_BROKER_URL` still overrides the app's broker if both are set. |
| `CELERY_INSPECT_TIMEOUT` | `1.0` | Seconds to wait for worker replies. Raise it for large or slow clusters. |

`CELERY_APP` has to be importable, so run the server from your project's directory and environment:

```bash
uv run --with mcp-server-celery mcp-server-celery
```

## Connect it

### Claude Code

```bash
claude mcp add celery -e CELERY_BROKER_URL=redis://localhost:6379/0 -- uvx mcp-server-celery
```

### Cursor

In `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "celery": {
      "command": "uvx",
      "args": ["mcp-server-celery"],
      "env": { "CELERY_BROKER_URL": "redis://localhost:6379/0" }
    }
  }
}
```

### Claude Desktop

In `claude_desktop_config.json`, use the same `command`, `args` and `env` block as Cursor, under `mcpServers`.

## Example

Ask the agent "why are my email tasks not running?" and it can call `queue_depths`:

```json
{
  "broker": "amqp://app:****@rabbit:5672//",
  "queues": [
    { "queue": "celery", "exists": true, "messages": 0, "consumers": 2, "workers_consuming": ["w1@web", "w2@web"] },
    { "queue": "emails", "exists": true, "messages": 1843, "consumers": 0, "workers_consuming": [] }
  ]
}
```

`emails` has a backlog and no worker consumes it: the workers were started without `-Q emails`.

## Notes on the data

- **Redis** has no notion of consumers, so `consumers` is `null`; use `workers_consuming`, which comes from the workers themselves. Redis also deletes a queue's key once it is empty, so a drained queue shows `"messages": 0, "exists": null`.
- **RabbitMQ** checks use a passive declare, so the server never creates a queue. A queue that doesn't exist shows `"exists": false`.
- Workers that are too busy to answer within `CELERY_INSPECT_TIMEOUT` don't appear in `list_workers`. If a worker you expect is missing, try a larger `timeout` argument before assuming it's dead.

## Safety

- Every tool is annotated `readOnlyHint: true`. Write actions (revoke, retry, purge) will only be available behind an explicit opt-in flag.
- URL credentials and `password`/`secret`/`token` fields are masked in all output and error messages.

## Roadmap

**v0.1** — `list_workers`, `queue_depths` ✅

**v1** — `active_tasks`, `reserved_tasks`, `scheduled_tasks`, `task_status(task_id)`, `diagnose_stuck`

**v2** — `summarize_failures`: groups recent failures by task name and exception type. Celery keeps no failure history by default, so this needs an event listener.

## Development

```bash
uv sync
uv run pytest tests/unit
uv run ruff check . && uv run ruff format --check .
```

Integration tests start a real worker and need a broker:

```bash
CELERY_BROKER_URL=redis://localhost:6379/0 uv run pytest tests/integration -m integration
```

CI runs them against Redis and RabbitMQ on every push.

## License

MIT
