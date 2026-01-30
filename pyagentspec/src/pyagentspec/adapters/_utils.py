# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import re
from typing import Any, Dict, List, Literal, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, create_model

from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import _empty_default as _agentspec_empty_default
from pyagentspec.templating import TEMPLATE_PLACEHOLDER_REGEXP


def render_nested_object_template(
    object: Any,
    inputs: Dict[str, Any],
) -> Any:
    """Renders any found variables between curly braces from any string in an object which can be an arbitrarily nested
    structure of dicts, lists, sets and tuples.

    Parameters
    ----------
    object : Any
        A potentially nested python object (str, bytes, dict, list, set, tuple)
    inputs : Dict[str, Any]
        The inputs to the variables

    Returns
    -------
    Any
        An object of the same type as the input object with all found template variables
        replaced according to the given inputs.

    """
    if isinstance(object, str):
        return render_template(object, inputs)
    elif isinstance(object, bytes):
        return render_nested_object_template(
            object.decode("utf-8", errors="replace"),
            inputs,
        )
    elif isinstance(object, dict):
        return {
            render_nested_object_template(
                k,
                inputs,
            ): render_nested_object_template(
                v,
                inputs,
            )
            for k, v in object.items()
        }
    elif isinstance(object, list) or isinstance(object, set) or isinstance(object, tuple):
        return object.__class__(
            [
                render_nested_object_template(
                    item,
                    inputs,
                )
                for item in object
            ]
        )
    else:
        return object


def render_template(template: str, inputs: Dict[str, Any]) -> str:
    """Render a prompt template using inputs."""
    if not isinstance(template, str):
        return str(template)
    return _recursive_template_splitting_rendering(
        template, [(input_title, input_value) for input_title, input_value in inputs.items()]
    )


def _recursive_template_splitting_rendering(template: str, inputs: List[Tuple[str, Any]]) -> str:
    """Recursively split and join the templates using the list of inputs."""
    if len(inputs) == 0:
        return template
    input_title, input_value = inputs[-1]
    splitting_regexp = TEMPLATE_PLACEHOLDER_REGEXP.replace(r"(\w+)", input_title)
    split_templates = re.split(splitting_regexp, template)
    rendered_split_templates = [
        _recursive_template_splitting_rendering(t, inputs[:-1]) for t in split_templates
    ]
    rendered_template = str(input_value).join(rendered_split_templates)
    return rendered_template


class SchemaRegistry:
    def __init__(self) -> None:
        self.models: Dict[str, type[BaseModel]] = {}


def _build_type_from_schema(
    name: str,
    schema: Dict[str, Any],
    registry: SchemaRegistry,
) -> Any:
    # Enum -> Literal[…]
    if "enum" in schema and isinstance(schema["enum"], list):
        values = schema["enum"]
        # Literal supports a tuple of literal values as a single subscription argument
        return Literal[tuple(values)]

    # anyOf / oneOf -> Union[…]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            variants = [
                _build_type_from_schema(f"{name}Alt{i}", s, registry)
                for i, s in enumerate(schema[key])
            ]
            return Union[tuple(variants)]

    t = schema.get("type")

    # list of types -> Union[…]
    if isinstance(t, list):
        variants = [
            _build_type_from_schema(f"{name}Alt{i}", {"type": subtype}, registry)
            for i, subtype in enumerate(t)
        ]
        return Union[tuple(variants)]

    # arrays
    if t == "array":
        items_schema = schema.get("items", {"type": "any"})
        item_type = _build_type_from_schema(f"{name}Item", items_schema, registry)
        return List[item_type]  # type: ignore
    # objects
    if t == "object" or ("properties" in schema or "required" in schema):
        # Create or reuse a Pydantic model for this object schema
        model_name = schema.get("title") or name
        unique_name = model_name
        suffix = 1
        while unique_name in registry.models:
            suffix += 1
            unique_name = f"{model_name}_{suffix}"

        props = schema.get("properties", {}) or {}
        required = set(schema.get("required", []))

        fields: Dict[str, Tuple[Any, Any]] = {}
        for prop_name, prop_schema in props.items():
            prop_type = _build_type_from_schema(f"{unique_name}_{prop_name}", prop_schema, registry)
            desc = prop_schema.get("description")
            default_field = (
                Field(..., description=desc)
                if prop_name in required
                else Field(None, description=desc)
            )
            fields[prop_name] = (prop_type, default_field)

        # Enforce additionalProperties: False (extra=forbid)
        extra_forbid = schema.get("additionalProperties") is False
        model_kwargs: Dict[str, Any] = {}
        if extra_forbid:
            # Pydantic v2: pass a ConfigDict/dict into __config__
            model_kwargs["__config__"] = ConfigDict(extra="forbid")

        model_cls = create_model(unique_name, **fields, **model_kwargs)  # type: ignore
        registry.models[unique_name] = model_cls
        return model_cls

    # primitives / fallback
    mapping = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "null": type(None),
        "any": Any,
        None: Any,
        "": Any,
    }
    return mapping.get(t, Any)


def create_pydantic_model_from_properties(
    model_name: str, properties: List[AgentSpecProperty]
) -> type[BaseModel]:
    registry = SchemaRegistry()
    fields: Dict[str, Tuple[Any, Any]] = {}

    for property_ in properties:
        # Build the annotation from the json_schema (handles enum/array/object/etc.)
        annotation = _build_type_from_schema(property_.title, property_.json_schema, registry)

        field_params: Dict[str, Any] = {}
        if property_.description:
            field_params["description"] = property_.description

        if property_.default is not _agentspec_empty_default:
            default_field = Field(property_.default, **field_params)
        else:
            default_field = Field(..., **field_params)

        fields[property_.title] = (annotation, default_field)

    return create_model(model_name, **fields)  # type: ignore
