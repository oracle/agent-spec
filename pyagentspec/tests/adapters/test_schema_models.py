# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""Pydantic models generated from Agent Spec JSON schemas keep the JSON Schema semantics."""

from copy import deepcopy
from typing import Any, Dict

import pytest
from pydantic import BaseModel, ValidationError

from pyagentspec.adapters._utils import (
    AgentSpecObjectModel,
    apply_json_schema_defaults,
    create_pydantic_model_from_properties,
    get_json_schema_validation_errors,
    to_json_value,
)
from pyagentspec.property import DictProperty, IntegerProperty, Property

REQUEST_SCHEMA: Dict[str, Any] = {
    "title": "request",
    "type": "object",
    "properties": {
        "customer_id": {"type": "string"},
        "profile": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        },
        "tags": {"type": "array", "items": {"type": "string"}},
        "priority": {"type": "string", "default": "normal"},
        "notifications": {"type": "boolean", "default": True},
        "note": {"type": "string"},
    },
    "required": ["customer_id", "profile", "tags"],
    "additionalProperties": False,
}

STATE_SCHEMA: Dict[str, Any] = {
    "title": "state",
    "type": "object",
    "properties": {
        "counter": {"type": "integer"},
        "trace": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["counter", "trace"],
    "additionalProperties": True,
}


def test_bare_object_schema_is_passed_through_as_dictionary() -> None:
    # oracle/agent-spec#220: an empty model used to silently strip every key
    model = create_pydantic_model_from_properties(
        "ToolArgs",
        [Property(title="components", json_schema={"type": "array", "items": {"type": "object"}})],
    )
    parsed = model(components=[{"id": "root", "component": "Card"}])
    assert to_json_value(parsed.components) == [{"id": "root", "component": "Card"}]


def test_typed_dictionary_schema_keeps_keys_and_validates_values() -> None:
    model = create_pydantic_model_from_properties(
        "ToolArgs", [DictProperty(title="scores", value_type=IntegerProperty())]
    )
    assert model(scores={"a": 1, "b": 2}).scores == {"a": 1, "b": 2}
    with pytest.raises(ValidationError):
        model(scores={"a": "not an integer"})


def test_additional_properties_are_kept_when_allowed() -> None:
    # oracle/agent-spec#239
    model = create_pydantic_model_from_properties("Args", [Property(json_schema=STATE_SCHEMA)])
    parsed = model(state={"counter": 1, "trace": ["step1"], "step1": "initialized"})
    assert isinstance(parsed.state, AgentSpecObjectModel)
    assert to_json_value(parsed.state) == {
        "counter": 1,
        "trace": ["step1"],
        "step1": "initialized",
    }


def test_additional_properties_are_kept_when_unspecified() -> None:
    schema = {key: value for key, value in STATE_SCHEMA.items() if key != "additionalProperties"}
    model = create_pydantic_model_from_properties("Args", [Property(json_schema=schema)])
    parsed = model(state={"counter": 1, "trace": [], "extra": "kept"})
    assert to_json_value(parsed.state) == {"counter": 1, "trace": [], "extra": "kept"}


def test_additional_properties_are_rejected_when_forbidden() -> None:
    model = create_pydantic_model_from_properties("Args", [Property(json_schema=REQUEST_SCHEMA)])
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model(
            request={
                "customer_id": "C-1042",
                "profile": {"name": "Ada", "age": 36},
                "tags": [],
                "extra": 1,
            }
        )


def test_declared_defaults_are_applied_and_unset_optionals_are_omitted() -> None:
    # oracle/agent-spec#241: omitted defaulted fields used to come out as None
    model = create_pydantic_model_from_properties("Args", [Property(json_schema=REQUEST_SCHEMA)])
    parsed = model(
        request={
            "customer_id": "C-1042",
            "profile": {"name": "Ada", "age": 36},
            "tags": ["priority", "verified"],
        }
    )
    assert to_json_value(parsed.request) == {
        "customer_id": "C-1042",
        "profile": {"name": "Ada", "age": 36},
        "tags": ["priority", "verified"],
        "priority": "normal",
        "notifications": True,
    }


def test_explicitly_provided_values_take_precedence_over_defaults() -> None:
    model = create_pydantic_model_from_properties("Args", [Property(json_schema=REQUEST_SCHEMA)])
    parsed = model(
        request={
            "customer_id": "C-1042",
            "profile": {"name": "Ada", "age": 36},
            "tags": [],
            "priority": "high",
            "notifications": False,
            "note": "call back",
        }
    )
    assert to_json_value(parsed.request) == {
        "customer_id": "C-1042",
        "profile": {"name": "Ada", "age": 36},
        "tags": [],
        "priority": "high",
        "notifications": False,
        "note": "call back",
    }


def test_nested_required_fields_are_still_validated() -> None:
    model = create_pydantic_model_from_properties("Args", [Property(json_schema=REQUEST_SCHEMA)])
    with pytest.raises(ValidationError, match="age"):
        model(request={"customer_id": "C-1042", "profile": {"name": "Ada"}, "tags": []})


def test_to_json_value_converts_nested_models_recursively() -> None:
    schema = {
        "title": "order",
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"sku": {"type": "string"}, "qty": {"type": "integer"}},
                    "required": ["sku"],
                },
            },
            "shipping": {
                "type": "object",
                "properties": {"express": {"type": "boolean", "default": False}},
            },
        },
        "required": ["items"],
    }
    model = create_pydantic_model_from_properties("Args", [Property(json_schema=schema)])
    parsed = model(order={"items": [{"sku": "A", "qty": 2}, {"sku": "B"}], "shipping": {}})
    assert to_json_value(parsed.order) == {
        "items": [{"sku": "A", "qty": 2}, {"sku": "B"}],
        "shipping": {"express": False},
    }


def test_to_json_value_leaves_foreign_models_untouched_and_converts_tuples() -> None:
    class ForeignArguments(BaseModel):
        value: int

    foreign = ForeignArguments(value=1)
    assert to_json_value({"model": foreign, "pair": (1, 2)}) == {"model": foreign, "pair": [1, 2]}
    assert to_json_value("text") == "text"


@pytest.mark.parametrize(
    "value, json_schema, expected",
    [
        (
            {"customer_id": "C-1"},
            REQUEST_SCHEMA,
            {"customer_id": "C-1", "priority": "normal", "notifications": True},
        ),
        # Provided values are not overwritten
        (
            {"customer_id": "C-1", "priority": "high"},
            REQUEST_SCHEMA,
            {"customer_id": "C-1", "priority": "high", "notifications": True},
        ),
        # Defaults are applied inside array items
        (
            [{"a": 1}, {}],
            {
                "type": "array",
                "items": {"type": "object", "properties": {"a": {"type": "integer", "default": 0}}},
            },
            [{"a": 1}, {"a": 0}],
        ),
        # Defaults are applied inside nested objects
        (
            {"inner": {}},
            {
                "type": "object",
                "properties": {
                    "inner": {
                        "type": "object",
                        "properties": {"flag": {"type": "boolean", "default": True}},
                    }
                },
            },
            {"inner": {"flag": True}},
        ),
        # Non-object values and untyped schemas are returned as they are
        ("text", {"type": "string", "default": "other"}, "text"),
        ({"a": 1}, {}, {"a": 1}),
    ],
)
def test_apply_json_schema_defaults(value: Any, json_schema: Dict[str, Any], expected: Any) -> None:
    original_value = deepcopy(value)
    assert apply_json_schema_defaults(value, json_schema) == expected
    # The input value is not mutated
    assert value == original_value


def test_apply_json_schema_defaults_copies_mutable_defaults() -> None:
    json_schema = {
        "type": "object",
        "properties": {"tags": {"type": "array", "items": {"type": "string"}, "default": []}},
    }
    first = apply_json_schema_defaults({}, json_schema)
    first["tags"].append("mutated")
    assert apply_json_schema_defaults({}, json_schema) == {"tags": []}


def test_get_json_schema_validation_errors() -> None:
    assert (
        get_json_schema_validation_errors(
            {"customer_id": "C-1", "profile": {"name": "Ada", "age": 36}, "tags": []},
            REQUEST_SCHEMA,
        )
        == []
    )
    errors = get_json_schema_validation_errors(
        {"customer_id": 1, "profile": {"name": "Ada"}, "tags": []}, REQUEST_SCHEMA
    )
    assert errors == [
        "$.customer_id: 1 is not of type 'string'",
        "$.profile: 'age' is a required property",
    ]
    # An empty schema accepts any value
    assert get_json_schema_validation_errors({"anything": [1, None]}, {}) == []
