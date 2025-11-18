# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the base class for the definition of inputs and outputs in Components."""
from collections import defaultdict
from typing import Any, ClassVar, Dict, List, Optional, Set, Union

from jsonschema.validators import Draft202012Validator
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    field_validator,
    model_serializer,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from typing_extensions import Self

from pyagentspec.validation_helpers import model_validator_with_error_accumulation

DEFAULT_TITLE = "property"


class _empty_default:
    """Marker object for Property.empty_default"""


def _validate_schema_titles(json_schema: JsonSchemaValue) -> None:
    """
    Validate that titles of a json_schema do not contain special characters or blank spaces.

    For recursive schemas such as unions, arrays or objects, the validation is also applied to the
    inner types recursively.
    """
    special_characters = ".,{} \n'\""
    schema_title = json_schema.get("title", "")
    if any(c in schema_title for c in special_characters):
        raise ValueError(
            f"Titles of properties should not contain special characters or blank space. "
            f"Found: '{schema_title}'"
        )
    if "items" in json_schema:
        _validate_schema_titles(json_schema["items"])
    for inner_schema in json_schema.get("anyOf", []):
        _validate_schema_titles(inner_schema)
    if "additionalProperties" in json_schema and not isinstance(
        json_schema["additionalProperties"], bool
    ):
        _validate_schema_titles(json_schema["additionalProperties"])
    for inner_schema in json_schema.get("properties", {}).values():
        _validate_schema_titles(inner_schema)


class Property(BaseModel):
    """
    Properties are the values that Components expose as inputs and outputs.

    Property encapsulates all the information about a Property.
    """

    model_config = ConfigDict(extra="forbid")

    json_schema: JsonSchemaValue = Field(default_factory=dict)
    title: str = DEFAULT_TITLE
    description: Optional[str] = None
    default: Optional[Any] = _empty_default
    type: Optional[Union[str, List[str]]] = None

    empty_default: ClassVar[Any] = _empty_default

    def model_post_init(self, __context: Any) -> None:
        """Perform additional validation and set automatically the values of some fields."""
        if self.title is DEFAULT_TITLE and "title" in self.json_schema:
            self.title = self.json_schema["title"]

        if self.description is None and "description" in self.json_schema:
            self.description = self.json_schema["description"]

        if self.default is Property.empty_default and "default" in self.json_schema:
            self.default = self.json_schema["default"]

        if self.type is None and "type" in self.json_schema:
            self.type = self.json_schema["type"]

    @model_validator_with_error_accumulation
    def _validate_default(self) -> Self:
        if self.default is Property.empty_default:
            return self
        if not value_is_of_compatible_type(self.default, self.json_schema):
            raise ValueError(
                f"The type of the default value of property {self.title} is not compatible with its json schema"
            )
        return self

    @classmethod
    def _set_json_schema(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        data["json_schema"] = {
            **data.get("json_schema", {}),  # passed json_schema
            **_build_json_schema(data),  # override with name/description/default value
            **cls._get_json_schema_specific_type(data),
        }
        return data

    @classmethod
    def model_construct(cls, _fields_set: Optional[Set[str]] = None, **kwargs: Any) -> "Property":
        # We need to override the model construct, as it's the only way to set the json_schema
        # attribute even when model validation is not performed
        kwargs = cls._set_json_schema(kwargs)
        return super().model_construct(_fields_set=_fields_set, **kwargs)

    @model_validator(mode="before")
    @classmethod
    def _validate_model_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        return cls._set_json_schema(data)

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {}

    @field_validator("json_schema")
    @classmethod
    def json_schema_is_valid(cls, schema: JsonSchemaValue) -> JsonSchemaValue:
        """
        Check if the given JSON schema is valid according to Draft 202012.

        In case of an invalid schema, an exception is raised.

        Parameters
        ----------
        schema:
            the JSON schema to validate

        Returns
        -------
        JsonSchemaValue
            The input JSON schema
        """
        Draft202012Validator.check_schema(schema)
        return schema

    @model_serializer()
    def serialize_model(self) -> JsonSchemaValue:
        """
        Serialize the model instance.

        Override the default pydantic solution.

        Returns
        -------
        JsonSchemaValue
            The JSON schema that represents the serialization of this model instance
        """
        # The dump of this model will be replaced by the json schema of the same object
        return self.json_schema

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
        /,
    ) -> JsonSchemaValue:
        """
        Overwrite the json schema for Property.

        The schema has to be aligned because ``parse_obj`` and ``serialize_model`` are overwritten

        Parameters
        ----------
        core_schema:
            A `pydantic-core` CoreSchema.
            You can ignore this argument and call the handler with a new CoreSchema,
            wrap this CoreSchema (`{'type': 'nullable', 'schema': current_schema}`),
            or just call the handler with the original schema.
        handler:
            Call into Pydantic's internal JSON schema generation.
            This will raise a `pydantic.errors.PydanticInvalidForJsonSchema` if JSON schema
            generation fails.
            Since this gets called by `BaseModel.model_json_schema` you can override the
            `schema_generator` argument to that function to change JSON schema generation globally
            for a type.

        Returns
        -------
            The overwritten schema for Property
        """
        return {"type": "object", "description": "This object must be a valid JSON Schema"}

    @model_validator(mode="after")
    def _validate_title(self) -> Self:
        _validate_schema_titles(self.json_schema)
        return self

    def __eq__(self, other: object) -> bool:
        # We enhance the basic identity equality provided by BaseModel
        # We assume two properties are equal if they have the same exact JSON schema
        if isinstance(other, Property):
            return self.json_schema == other.json_schema
        return False


def _build_json_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    json_schema = {}
    if "title" in data:
        json_schema["title"] = data["title"]
    if "description" in data:
        json_schema["description"] = data["description"]
    if "default" in data:
        json_schema["default"] = data["default"]
    if "type" in data:
        json_schema["type"] = data["type"]
    return json_schema


class StringProperty(Property):
    """Property object to represent a string property."""

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {"type": "string"}


class BooleanProperty(Property):
    """Property object to represent a boolean property."""

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {"type": "boolean"}


class IntegerProperty(Property):
    """Property object to represent an integer property."""

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {"type": "integer"}


class NumberProperty(Property):
    """Property object to represent a number property."""

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {"type": "number"}


class FloatProperty(NumberProperty):
    """Equivalent of a number property."""


class NullProperty(Property):
    """Property object to represent a null property."""

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {"type": "null"}


class UnionProperty(Property):
    """Property object to represent a union property."""

    any_of: List[Property]

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {"anyOf": [item.json_schema for item in data["any_of"]]}


class ListProperty(Property):
    """Property object to represent a list property."""

    item_type: Property

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {
            "items": data["item_type"].json_schema,
            "type": "array",
        }


class DictProperty(Property):
    """Property object to represent a dict property."""

    value_type: Property

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {
            "additionalProperties": data["value_type"].json_schema,
            "properties": {},
            "type": "object",
        }


class ObjectProperty(Property):
    """Property object to represent an object property."""

    properties: Dict[str, Property]

    @classmethod
    def _get_json_schema_specific_type(cls, data: Dict[str, Any]) -> JsonSchemaValue:
        return {
            "properties": {
                prop_name: prop_value.json_schema
                for prop_name, prop_value in data["properties"].items()
            },
            "type": "object",
        }


def properties_have_same_type(property_a: "Property", property_b: "Property") -> bool:
    return json_schemas_have_same_type(
        json_schema_a=property_a.json_schema,
        json_schema_b=property_b.json_schema,
    )


MAX_JSON_SCHEMA_UNION_TYPE_ALLOWED_LENGTH = 100


def _normalize_json_schema_union_types(schema: JsonSchemaValue) -> List[JsonSchemaValue]:
    # Normalization merges the basic types and anyOf for a schema
    # and returns a list containing all the schemas.
    json_schema_type = schema.get("type", [])
    json_schema_types = (
        json_schema_type if isinstance(json_schema_type, list) else [json_schema_type]
    )
    all_types: List[JsonSchemaValue] = schema.get("anyOf", [])
    for json_schema_type in json_schema_types:
        if json_schema_type == "array":
            # If one of the basic types is array, we put the items definition in it
            all_types.append({"type": "array", "items": schema.get("items", {})})
        elif json_schema_type == "object":
            # If one of the basic types is object, we put the properties definition in it
            all_types.append(
                {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "additionalProperties": schema.get("additionalProperties", False),
                }
            )
        else:
            # Normally we just carry over the basic type
            all_types.append({"type": json_schema_type})

    if len(all_types) > MAX_JSON_SCHEMA_UNION_TYPE_ALLOWED_LENGTH:
        raise RuntimeError(
            f"The schema is the union of more than {MAX_JSON_SCHEMA_UNION_TYPE_ALLOWED_LENGTH}"
            " types. This is not supported. Please consider simplifying the type definition or"
            " using 'Any'."
        )
    return all_types


def json_schemas_have_same_type(
    json_schema_a: JsonSchemaValue, json_schema_b: JsonSchemaValue
) -> bool:
    """Check if the two schemas define the same type"""
    if "allOf" in json_schema_a or "allOf" in json_schema_b:
        raise NotImplementedError("Support for schemas using allOf is not implemented.")
    if "oneOf" in json_schema_a or "oneOf" in json_schema_b:
        raise NotImplementedError("Support for schemas using oneOf is not implemented.")
    # Basic types must match
    if (
        "anyOf" in json_schema_a
        or isinstance(json_schema_a.get("type"), list)
        or "anyOf" in json_schema_b
        or isinstance(json_schema_b.get("type"), list)
    ):
        # We need to combine anyOf and the list of types specified in type
        # We normalize them to another json_schema, so that we can compare them afterward using this method
        json_schema_a_type_list = _normalize_json_schema_union_types(json_schema_a)
        json_schema_b_type_list = _normalize_json_schema_union_types(json_schema_b)
        # We make sure that the set of possible types overlap correctly (same elements)
        # We cannot check the length directly, as the same type could be repeated
        for json_schema_a_type in json_schema_a_type_list:
            if not any(
                json_schemas_have_same_type(json_schema_a_type, json_schema_b_type)
                for json_schema_b_type in json_schema_b_type_list
            ):
                return False
        for json_schema_b_type in json_schema_b_type_list:
            if not any(
                json_schemas_have_same_type(json_schema_a_type, json_schema_b_type)
                for json_schema_a_type in json_schema_a_type_list
            ):
                return False
        # We flattened everything in the anyOf, so no need to go on with the checks
        return True
    else:
        if json_schema_a.get("type") != json_schema_b.get("type"):
            return False
    # If it's an array, the items type must match
    if "items" in json_schema_a or "items" in json_schema_b:
        if not json_schemas_have_same_type(
            json_schema_a.get("items", {}),
            json_schema_b.get("items", {}),
        ):
            return False
    # If it's an object, the set of properties must match, and their type must match too
    if "properties" in json_schema_a or "properties" in json_schema_b:
        if json_schema_a.get("properties", {}).keys() != json_schema_b.get("properties", {}).keys():
            return False
        for property_name in json_schema_a["properties"]:
            if not json_schemas_have_same_type(
                json_schema_a["properties"][property_name],
                json_schema_b["properties"][property_name],
            ):
                return False
    if "additionalProperties" in json_schema_a or "additionalProperties" in json_schema_b:
        json_schema_a_additional_properties = json_schema_a.get("additionalProperties", {})
        json_schema_b_additional_properties = json_schema_b.get("additionalProperties", {})
        # If any of the two additional properties is a boolean, we check strict equality (bool == dict is always false)
        if isinstance(json_schema_a_additional_properties, bool) or isinstance(
            json_schema_b_additional_properties, bool
        ):
            return bool(json_schema_a_additional_properties == json_schema_b_additional_properties)
        if not json_schemas_have_same_type(
            json_schema_a_additional_properties, json_schema_b_additional_properties
        ):
            return False
    return True


def property_is_castable_to(property_a: Property, property_b: Property) -> bool:
    return json_schema_is_castable_to(
        property_a.json_schema,
        property_b.json_schema,
    )


def json_schema_is_castable_to(schema_a: JsonSchemaValue, schema_b: JsonSchemaValue) -> bool:
    """Check if the first json schema has a type that can be casted to the second"""
    if "allOf" in schema_a or "allOf" in schema_b:
        raise NotImplementedError("Support for schemas using allOf is not implemented.")
    if "oneOf" in schema_a or "oneOf" in schema_b:
        raise NotImplementedError("Support for schemas using oneOf is not implemented.")
    if schema_a == schema_b:
        return True
    if not any(t in schema_b for t in ["type", "anyOf"]):
        # No type in the json_schema represents the equivalent of 'Any' for json schema.
        # Every type is castable to Any.
        return True
    if schema_b.get("type") == "string":
        # Every value of any type can be cast to a string
        return True
    if (
        "anyOf" in schema_a
        or isinstance(schema_a.get("type"), list)
        or "anyOf" in schema_b
        or isinstance(schema_b.get("type"), list)
    ):
        # We need to combine anyOf and the list of types specified in type
        # We normalize them to another json_schema, so that we can compare them afterward using this method
        schema_a_type_list = _normalize_json_schema_union_types(schema_a)
        schema_b_type_list = _normalize_json_schema_union_types(schema_b)
        # We make sure that all the types of the first json schema are contained in the second
        for json_schema_a_type in schema_a_type_list:
            if not any(
                json_schema_is_castable_to(json_schema_a_type, json_schema_b_type)
                for json_schema_b_type in schema_b_type_list
            ):
                return False
        # We flattened everything in the anyOf, so no need to go on with the checks
        return True

    numerical_types = {"number", "integer", "boolean"}
    if schema_a.get("type") in numerical_types and schema_b.get("type") in numerical_types:
        return True
    if schema_a.get("type") == "array" and schema_b.get("type") == "array":
        return json_schema_is_castable_to(
            schema_a.get("items", {}),
            schema_b.get("items", {}),
        )
    # If it's an object, the set of properties of schema a must be a superset of the set of
    # properties of schema b so that the object is castable, and their type must also be
    # castable.
    if schema_a.get("type") == "object" and schema_b.get("type") == "object":
        properties_a, properties_b = schema_a.get("properties", {}), schema_b.get("properties", {})
        for property_name, property_type in properties_b.items():
            if property_name not in properties_a or not json_schema_is_castable_to(
                properties_a[property_name], property_type
            ):
                return False

        schema_a_additional_properties = schema_a.get("additionalProperties", {})
        schema_b_additional_properties = schema_b.get("additionalProperties", {})
        # If any of the two additional properties is a boolean, we check strict equality (bool == dict is always false)
        if isinstance(schema_a_additional_properties, bool) or isinstance(
            schema_b_additional_properties, bool
        ):
            return bool(schema_a_additional_properties == schema_b_additional_properties)
        if not json_schema_is_castable_to(
            schema_a_additional_properties, schema_b_additional_properties
        ):
            return False
        return True
    return False


def value_is_of_compatible_type(value: Any, json_schema: JsonSchemaValue) -> bool:
    if "anyOf" in json_schema or isinstance(json_schema.get("type"), list):
        # We need to combine anyOf and the list of types specified in type
        # We normalize them to another json_schema, so that we can compare them afterward using this method
        schema_type_list = _normalize_json_schema_union_types(json_schema)
        # We make sure that the value is compatible with at least one type among the available ones
        return any(
            value_is_of_compatible_type(value, json_schema_type)
            for json_schema_type in schema_type_list
        )
    schema_type = json_schema.get("type")
    # Null type corresponds to None only
    if schema_type == "null":
        return value is None
    # Numerical types are all compatible between each other
    numerical_types = {"number", "integer", "boolean"}
    if schema_type in numerical_types:
        return isinstance(value, (int, float, bool))
    # If we have an array, we have to check that all the elements are of a compatible type
    if schema_type == "array":
        if not isinstance(value, list):
            # We accept only lists as they are the only available in json schema,
            # we do not accept other python data structures like sets or tuples
            return False
        return all(
            value_is_of_compatible_type(inner_value, json_schema.get("items", {}))
            for inner_value in value
        )
    if schema_type == "object":
        # Objects must be dictionaries in python
        if not isinstance(value, dict):
            return False
        # We go through the expected properties, and we check that they exist, and they are of the right type
        properties = json_schema.get("properties", {})
        for property_name, property_type in properties.items():
            if property_name in value:
                if not value_is_of_compatible_type(value[property_name], property_type):
                    return False
            elif "default" not in property_type:
                # We accept that a property is not in the given value if a default is defined in the json schema
                return False
        # The properties that are not defined in json schema `properties` entry are supported as additionalProperties
        additional_properties_type = json_schema.get("additionalProperties", {})
        # We have to check their types as well
        for property_name, inner_value in value.items():
            if property_name not in properties:
                # First we check whether additional properties were allowed, if they were not, we return false
                if additional_properties_type is False:
                    return False
                # Then we make sure that the additional property has they right type
                if not value_is_of_compatible_type(inner_value, additional_properties_type):
                    return False
    return True


def deduplicate_properties_by_title_and_type(properties: List[Property]) -> List[Property]:
    """Deduplicates all properties with the same title and type in a list."""

    properties_by_title: Dict[str, List[Property]] = defaultdict(list)
    for property_ in properties:
        properties_by_title[property_.title].append(property_)

    deduplicated_properties: List[Property] = []

    for title, property_list in properties_by_title.items():
        distinct_property_types: List[Property] = []
        for property_ in property_list:
            new_property_type = True
            for already_deduplicated_property in distinct_property_types:
                if json_schemas_have_same_type(
                    property_.json_schema, already_deduplicated_property.json_schema
                ):
                    new_property_type = False
                    break

            if new_property_type:
                distinct_property_types.append(property_)

        deduplicated_properties.extend(distinct_property_types)

    return deduplicated_properties
