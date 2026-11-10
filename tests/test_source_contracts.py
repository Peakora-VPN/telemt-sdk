"""Contracts extracted from pinned Rust serialization types, independent of SDK declarations."""

import json
from pathlib import Path
from types import UnionType
from typing import Union, get_args, get_origin

import pytest

from telemt import models as m

CONTRACTS = json.loads((Path(__file__).parent / "fixtures/source-contracts.json").read_text())


def annotation_name(annotation):
    if annotation is type(None):
        return "None"
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        return " | ".join(annotation_name(arg) for arg in get_args(annotation))
    if origin is not None:
        return (
            origin.__name__
            + "["
            + ", ".join(annotation_name(arg) for arg in get_args(annotation))
            + "]"
        )
    return annotation.__name__


@pytest.mark.parametrize(("name", "contract"), CONTRACTS["models"].items())
def test_rust_serialized_fields_and_types(name, contract):
    model = getattr(m, name)
    fields = {field.alias or name: field for name, field in model.model_fields.items()}
    assert fields.keys() == contract["fields"].keys(), contract["source"]
    for field_name, expected in contract["fields"].items():
        field = fields[field_name]
        assert annotation_name(field.annotation) == expected["type"], (name, field_name)
        if expected["omittable"]:
            assert not field.is_required(), (name, field_name)


def test_all_response_models_are_in_source_inventory():
    names = {
        name
        for name in m.__all__
        if isinstance(model := getattr(m, name), type) and issubclass(model, m.ResponseModel)
    }
    # Envelopes and the open config document are constructed as JSON in Rust handlers.
    assert names - {
        "APIResponse",
        "ResponseModel",
        "ConfigData",
        "ErrorDetail",
        "ErrorEnvelope",
        "NullableRevisionAPIResponse",
    } == (CONTRACTS["models"].keys())
