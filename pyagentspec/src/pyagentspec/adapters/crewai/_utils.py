# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, List

from pydantic import BaseModel, Field, create_model

from pyagentspec.property import Property as AgentSpecProperty
from pyagentspec.property import _empty_default as _agentspec_empty_default


def _json_schema_type_to_python_annotation(json_schema: Dict[str, Any]) -> str:
    if "anyOf" in json_schema:
        possible_types = set(
            _json_schema_type_to_python_annotation(inner_json_schema_type)
            for inner_json_schema_type in json_schema["anyOf"]
        )
        return f"Union[{','.join(possible_types)}]"
    if isinstance(json_schema["type"], list):
        possible_types = set(
            _json_schema_type_to_python_annotation(inner_json_schema_type)
            for inner_json_schema_type in json_schema["type"]
        )
        return f"Union[{','.join(possible_types)}]"
    mapping = {
        "string": "str",
        "number": "float",
        "integer": "int",
        "boolean": "bool",
        "null": "None",
    }
    if json_schema["type"] == "object":
        # We could do better in inferring the type of values, for now we just use Any
        return "Dict[str, Any]"
    if json_schema["type"] == "array":
        return f"List[{_json_schema_type_to_python_annotation(json_schema['items'])}]"
    return mapping.get(json_schema["type"], "Any")


def create_pydantic_model_from_properties(
    model_name: str, properties: List[AgentSpecProperty]
) -> type[BaseModel]:
    """Create a Pydantic model CLASS whose attributes are the given properties."""
    fields: Dict[str, Any] = {}
    for property_ in properties:
        field_parameters: Dict[str, Any] = {}
        param_name = property_.title
        if property_.default is not _agentspec_empty_default:
            field_parameters["default"] = property_.default
        if property_.description:
            field_parameters["description"] = property_.description
        annotation = _json_schema_type_to_python_annotation(property_.json_schema)
        fields[param_name] = (annotation, Field(**field_parameters))
    return create_model(model_name, **fields)
