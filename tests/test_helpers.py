import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from telemt.models import SessionQuery
from telemt.resources import SystemResource, WebResource


@pytest.mark.parametrize(
    "resource,method,poll,terminal",
    [
        (SystemResource, "wait_reload", "reload_status", "succeeded"),
        (SystemResource, "wait_reload", "reload_status", "rolled_back"),
        (SystemResource, "wait_reload", "reload_status", "failed"),
        (WebResource, "wait_operation", "operation", "completed"),
        (WebResource, "wait_operation", "operation", "failed"),
    ],
)
async def test_wait(resource, method, poll, terminal):
    obj = resource(None)
    final = SimpleNamespace(data=SimpleNamespace(state=terminal))
    mock = AsyncMock(side_effect=[SimpleNamespace(data=SimpleNamespace(state="pending")), final])
    setattr(obj, poll, mock)
    assert await getattr(obj, method)(1, poll_interval=0.001) is final
    assert mock.await_count == 2


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan"), True])
async def test_invalid_limits(value):
    with pytest.raises(ValueError):
        await SystemResource(None).wait_reload(1, timeout=value)
    with pytest.raises(ValueError):
        await WebResource(None).wait_operation("unused", poll_interval=value)


async def test_deadline_and_cancellation():
    obj = SystemResource(None)

    async def slow(_):
        await asyncio.sleep(10)

    obj.reload_status = slow
    with pytest.raises(TimeoutError):
        await obj.wait_reload(1, timeout=0.001)
    task = asyncio.create_task(obj.wait_reload(1))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_pagination_preserves_query():
    obj = WebResource(None)
    cursor = "ws1." + "a" * 32 + ".0000000000000001"
    query = SessionQuery(user="alice", limit=10)
    obj.sessions = AsyncMock(
        side_effect=[
            SimpleNamespace(data=SimpleNamespace(sessions=["one"], next_cursor=cursor)),
            SimpleNamespace(data=SimpleNamespace(sessions=["two"], next_cursor=None)),
        ]
    )
    assert [row async for row in obj.iter_sessions(query)] == ["one", "two"]
    assert query.cursor is None
    second = obj.sessions.call_args_list[1].args[0]
    assert (second.user, second.limit, second.cursor) == ("alice", 10, cursor)


async def test_repeated_cursor():
    obj = WebResource(None)
    cursor = "ws1." + "a" * 32 + ".0000000000000001"
    obj.sessions = AsyncMock(
        return_value=SimpleNamespace(data=SimpleNamespace(sessions=[], next_cursor=cursor))
    )
    with pytest.raises(ValueError, match="repeated"):
        _ = [row async for row in obj.iter_sessions()]
