# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import re
from copy import deepcopy
from typing import Any, ClassVar, Dict, FrozenSet, List, Literal, Tuple, Union

from jsonschema import Draft202012Validator
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


def render_template(template: Any, inputs: Dict[str, Any]) -> str:
    """Render a prompt template using inputs."""
    if not isinstance(template, str):
        return str(template)
    return _render_template_placeholders(template, inputs)


def _render_template_placeholders(template: str, inputs: Dict[str, Any]) -> str:
    """Render placeholders found in the original template using the list of inputs."""
    rendered_parts: List[str] = []
    last_end: int = 0

    for match in re.finditer(TEMPLATE_PLACEHOLDER_REGEXP, template):
        rendered_parts.append(template[last_end : match.start()])
        # Original placeholder text as it appeared in the template, including braces and inner whitespace
        full_placeholder = match.group(0)
        # Only the placeholder name, extracted from inside {{ ... }}
        input_title = match.group(1)
        if input_title in inputs:
            rendered_parts.append(str(inputs[input_title]))
        else:
            rendered_parts.append(full_placeholder)
        last_end = match.end()

    rendered_parts.append(template[last_end:])
    return "".join(rendered_parts)


class SchemaRegistry:
    def __init__(self) -> None:
        self.models: Dict[str, type[BaseModel]] = {}


class AgentSpecObjectModel(BaseModel):
    """Base class of the pydantic models generated from Agent Spec object schemas.

    The generated models keep the JSON Schema semantics of the property they come from:
    additional keys are kept when the schema allows them, declared defaults are applied,
    and optional fields that were neither provided nor defaulted are omitted when the
    model is converted back to a plain JSON value with :func:`to_json_value`.
    """

    _agentspec_fields_with_default: ClassVar[FrozenSet[str]] = frozenset()

    def to_json_value(self) -> Dict[str, Any]:
        """Convert the model back to the plain JSON object it was validated from."""
        result: Dict[str, Any] = {}
        for field_name in type(self).model_fields:
            if (
                field_name in self.model_fields_set
                or field_name in self._agentspec_fields_with_default
            ):
                result[field_name] = to_json_value(getattr(self, field_name))
        for extra_name, extra_value in (self.model_extra or {}).items():
            result[extra_name] = to_json_value(extra_value)
        return result


class _AllowExtraObjectModel(AgentSpecObjectModel):
    """Generated object model for schemas that allow additional properties."""

    model_config = ConfigDict(extra="allow")


class _ForbidExtraObjectModel(AgentSpecObjectModel):
    """Generated object model for schemas with ``additionalProperties: false``."""

    model_config = ConfigDict(extra="forbid")


def to_json_value(value: Any) -> Any:
    """Recursively convert generated object models (and tuples) into plain JSON values.

    Pydantic models that do not come from Agent Spec schemas are left untouched so that
    runtime-specific tools keep receiving their own argument models.
    """
    if isinstance(value, AgentSpecObjectModel):
        return value.to_json_value()
    if isinstance(value, dict):
        return {key: to_json_value(inner_value) for key, inner_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_value(inner_value) for inner_value in value]
    return value


def apply_json_schema_defaults(value: Any, json_schema: Dict[str, Any]) -> Any:
    """Fill the declared defaults of missing object properties, recursively.

    Only object ``properties`` and array ``items`` are traversed; ``anyOf`` alternatives are
    left untouched because the matching alternative cannot be determined reliably.
    """
    if isinstance(value, dict):
        properties = json_schema.get("properties") or {}
        if not isinstance(properties, dict):
            return value
        result = dict(value)
        for property_name, property_schema in properties.items():
            if not isinstance(property_schema, dict):
                continue
            if property_name in result:
                result[property_name] = apply_json_schema_defaults(
                    result[property_name], property_schema
                )
            elif "default" in property_schema:
                result[property_name] = deepcopy(property_schema["default"])
        return result
    if isinstance(value, list):
        items_schema = json_schema.get("items")
        if isinstance(items_schema, dict):
            return [apply_json_schema_defaults(item, items_schema) for item in value]
    return value


def get_json_schema_validation_errors(value: Any, json_schema: Dict[str, Any]) -> List[str]:
    """Return human-readable validation errors of ``value`` against ``json_schema``.

    An empty list means the value conforms to the schema.
    """
    validator = Draft202012Validator(json_schema)
    errors = sorted(validator.iter_errors(value), key=lambda error: error.json_path)
    return [f"{error.json_path}: {error.message}" for error in errors]


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
        props = schema.get("properties", {}) or {}
        # JSON Schema allows additional properties unless the schema says otherwise
        additional_properties = schema.get("additionalProperties", True)

        if not props and additional_properties is not False:
            # Bare object schema (or a typed dictionary): any object is accepted, so the value
            # is passed through as a dictionary. An empty pydantic model would silently strip
            # every key instead.
            value_type = (
                _build_type_from_schema(f"{name}Value", additional_properties, registry)
                if isinstance(additional_properties, dict)
                else Any
            )
            return Dict[str, value_type]  # type: ignore

        # Create or reuse a Pydantic model for this object schema
        model_name = schema.get("title") or name
        unique_name = model_name
        suffix = 1
        while unique_name in registry.models:
            suffix += 1
            unique_name = f"{model_name}_{suffix}"

        required = set(schema.get("required", []))

        fields: Dict[str, Tuple[Any, Any]] = {}
        fields_with_default = set()
        for prop_name, prop_schema in props.items():
            prop_type = _build_type_from_schema(f"{unique_name}_{prop_name}", prop_schema, registry)
            desc = prop_schema.get("description")
            if prop_name in required:
                default_field = Field(..., description=desc)
            elif "default" in prop_schema:
                # Omitted optional properties take their declared default
                default_field = Field(deepcopy(prop_schema["default"]), description=desc)
                fields_with_default.add(prop_name)
            else:
                default_field = Field(None, description=desc)
            fields[prop_name] = (prop_type, default_field)

        # additionalProperties: False -> extra=forbid, otherwise keep the extra keys (extra=allow)
        base_model = (
            _ForbidExtraObjectModel if additional_properties is False else _AllowExtraObjectModel
        )

        model_cls = create_model(unique_name, __base__=base_model, **fields)  # type: ignore
        model_cls._agentspec_fields_with_default = frozenset(fields_with_default)
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


def _get_obj_reference(obj: Any) -> str:
    """
    Return a reference for the given object.
    Used in Runtime to Agent Spec converters to store converted objects in the registry.
    """
    return f"{obj.__class__.__name__.lower()}/{id(obj)}"
