# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the serialization plugin for Pydantic Components."""

from enum import Enum
from typing import Any, Dict, List, Mapping, Type

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from pyagentspec.component import Component
from pyagentspec.sensitive_field import is_sensitive_field
from pyagentspec.serialization.serializationcontext import SerializationContext
from pyagentspec.serialization.serializationplugin import ComponentSerializationPlugin


class _NestedSensitiveValueState(Enum):
    """How a nested BaseModel inside a sensitive field should be serialized."""

    HAS_VALUE = "has_value"
    ALL_EMPTY = "all_empty"
    NO_SENSITIVE_FIELDS = "no_sensitive_fields"


class PydanticComponentSerializationPlugin(ComponentSerializationPlugin):
    """Serialization plugin for Pydantic Components."""

    @staticmethod
    def _get_nested_sensitive_value_state(
        value: BaseModel,
    ) -> _NestedSensitiveValueState:
        """Classify how nested sensitive fields affect serialization.

        Sensitive BaseModels fall into three cases:
        - at least one nested sensitive field is populated
        - nested sensitive fields exist but they are all empty
        - no nested sensitive fields exist, so the caller should use the existing
          whole-model fallback logic
        """
        has_nested_sensitive_field = False
        for nested_field_name, nested_field_info in value.__class__.model_fields.items():
            if not is_sensitive_field(nested_field_info):
                continue
            has_nested_sensitive_field = True
            if PydanticComponentSerializationPlugin._sensitive_field_has_value(
                getattr(value, nested_field_name), nested_field_info
            ):
                return _NestedSensitiveValueState.HAS_VALUE
        if has_nested_sensitive_field:
            return _NestedSensitiveValueState.ALL_EMPTY
        return _NestedSensitiveValueState.NO_SENSITIVE_FIELDS

    @staticmethod
    def _sensitive_field_has_value(value: Any, field_info: FieldInfo) -> bool:
        """Return whether a sensitive field carries non-empty data."""
        if isinstance(value, BaseModel):
            nested_sensitive_value_state = (
                PydanticComponentSerializationPlugin._get_nested_sensitive_value_state(value)
            )
            match nested_sensitive_value_state:
                case _NestedSensitiveValueState.HAS_VALUE:
                    return True
                case _NestedSensitiveValueState.ALL_EMPTY:
                    return False
                case _NestedSensitiveValueState.NO_SENSITIVE_FIELDS:
                    pass
            # BaseModels without nested sensitive fields keep the existing whole-model
            # fallback logic below.
            if field_info.is_required():
                return True
            default_value = field_info.get_default(call_default_factory=True)
            if (
                isinstance(default_value, BaseModel)
                and value.__class__ is not default_value.__class__
            ):
                return True
            # Empty BaseModel defaults should remain inline so they do not require an
            # external component-registry entry during deserialization.
            return bool(value.model_dump(exclude_defaults=True, exclude_none=True))
        return bool(value)

    def __init__(
        self,
        component_types_and_models: Mapping[str, Type[BaseModel]],
        _allow_partial_model_serialization: bool = False,
    ) -> None:
        """
        Instantiate a Pydantic serialization plugin.

        component_types_and_models:
            Mapping of component classes by their class name.
        _allow_partial_model_serialization:
            Whether to raise an exception during serialization if the BaseModel is missing some fields
        """
        self._supported_component_types = list(component_types_and_models.keys())
        self.component_types_and_models = dict(component_types_and_models)
        self._allow_partial_model_serialization = _allow_partial_model_serialization

    @property
    def plugin_name(self) -> str:
        """Return the plugin name."""
        return "PydanticComponentPlugin"

    @property
    def plugin_version(self) -> str:
        """Return the plugin version."""
        from pyagentspec import __version__

        return __version__

    def supported_component_types(self) -> List[str]:
        """Indicate what component types the plugin supports."""
        return self._supported_component_types

    def serialize(
        self, component: Component, serialization_context: SerializationContext
    ) -> Dict[str, Any]:
        """Serialize a Pydantic component."""
        serialized_component: Dict[str, Any] = {}

        model_fields = component.get_versioned_model_fields(serialization_context.agentspec_version)
        for field_name, field_info in model_fields.items():
            if getattr(field_info, "exclude", False):  # To not include AIR version
                continue

            try:
                field_value = getattr(component, field_name)
                # If a sensitive value is left as a falsy value (e.g. None, False, {}, "") then it
                # is not replaced by a reference, such that the empty value does not need to be
                # explicitly specified when loading the component configuration.
                if is_sensitive_field(field_info) and self._sensitive_field_has_value(
                    field_value, field_info
                ):
                    serialized_component[field_name] = {
                        "$component_ref": f"{component.id}.{field_name}"
                    }
                else:
                    serialized_component[field_name] = serialization_context.dump_field(
                        value=field_value, info=field_info
                    )
            except AttributeError as e:
                if self._allow_partial_model_serialization:
                    continue
                raise e

        return serialized_component
