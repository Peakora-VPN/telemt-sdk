"""Replay responses from the real pinned Telemt binary through every SDK resource."""

import json
from pathlib import Path

import httpx
import pytest

from telemt import models as m

from .test_resources import READ_ROUTES, WRITE_ROUTES, resolve

RECORDS = json.loads((Path(__file__).parent / "fixtures/live-responses.json").read_text())
ARGS = {name: args for name, _, args in READ_ROUTES}
ARGS.update({name: args for name, _, _, args, _ in WRITE_ROUTES})


@pytest.mark.parametrize("record", RECORDS, ids=lambda row: row["method"])
async def test_real_response_through_resource(mock_api, record):
    client, _, responses = mock_api
    responses.append(httpx.Response(record["status_code"], json=record["body"]))
    result = await resolve(client, record["method"])(*ARGS[record["method"]])
    assert result.status_code == record["status_code"]
    assert result.revision == record["body"]["revision"]
    assert result.ok is True
    assert_no_untyped_fields(result.data)


def assert_no_untyped_fields(value):
    if isinstance(value, m.ConfigData):
        return  # Configuration is an intentionally open document in the upstream API.
    if isinstance(value, m.ResponseModel):
        assert not value.model_extra, (type(value).__name__, value.model_extra)
        for name in type(value).model_fields:
            assert_no_untyped_fields(getattr(value, name))
    elif isinstance(value, (list, tuple)):
        for item in value:
            assert_no_untyped_fields(item)


def test_real_responses_cover_every_canonical_operation():
    assert {row["method"] for row in RECORDS} == ARGS.keys()
