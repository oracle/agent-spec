"""A bare ``{"type": "object"}`` schema (no declared properties) must map to a
passthrough dict, not an empty pydantic model that silently strips every key
the LLM supplies (pydantic defaults to ``extra="ignore"``)."""

from typing import Any, Dict

from pyagentspec.adapters._utils import create_pydantic_model_from_properties
from pyagentspec.property import Property


def _model_for(json_schema: Dict[str, Any]) -> Any:
    prop = Property(title="components", json_schema=json_schema)
    return create_pydantic_model_from_properties("ToolArgs", [prop])


def test_array_of_bare_objects_keeps_item_keys() -> None:
    model = _model_for({"type": "array", "items": {"type": "object"}})

    parsed = model(
        components=[{"id": "root", "component": "Card", "child": "title"}]
    )

    assert parsed.components == [
        {"id": "root", "component": "Card", "child": "title"}
    ]


def test_bare_object_keeps_keys() -> None:
    model = _model_for({"type": "object"})

    parsed = model(components={"id": "root", "nested": {"a": 1}})

    assert parsed.components == {"id": "root", "nested": {"a": 1}}


def test_object_with_declared_properties_still_builds_a_model() -> None:
    model = _model_for(
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
    )

    parsed = model(components={"name": "Alice"})

    assert parsed.components.name == "Alice"
