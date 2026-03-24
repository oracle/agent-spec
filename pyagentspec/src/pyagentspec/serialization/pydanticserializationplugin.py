# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the serialization plugin for Pydantic Components."""

from typing import Any, Dict, List, Mapping, Type

from pydantic import BaseModel

from pyagentspec.component import Component
from pyagentspec.sensitive_field import is_sensitive_field
from pyagentspec.serialization.serializationcontext import SerializationContext
from pyagentspec.serialization.serializationplugin import ComponentSerializationPlugin


class PydanticComponentSerializationPlugin(ComponentSerializationPlugin):
    """Serialization plugin for Pydantic Components."""

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
                if is_sensitive_field(field_info) and field_value:
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
