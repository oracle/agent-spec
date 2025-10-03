# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines the serialization plugin for Pydantic Components."""

from typing import Any, Dict, List, Mapping, Type

from pydantic import BaseModel

from pyagentspec.component import Component
from pyagentspec.serialization.serializationcontext import SerializationContext
from pyagentspec.serialization.serializationplugin import ComponentSerializationPlugin


class PydanticComponentSerializationPlugin(ComponentSerializationPlugin):
    """Serialization plugin for Pydantic Components."""

    def __init__(self, component_types_and_models: Mapping[str, Type[BaseModel]]) -> None:
        """
        Instantiate a Pydantic serialization plugin.

        component_types_and_models:
            Mapping of component classes by their class name.
        """
        self._supported_component_types = list(component_types_and_models.keys())
        self.component_types_and_models = dict(component_types_and_models)

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

        for field_name, field_info in component.__class__.model_fields.items():
            if getattr(field_info, "exclude", False):  # To not include AIR version
                continue

            field_value = getattr(component, field_name)

            serialized_component[field_name] = serialization_context.dump_field(
                value=field_value, info=field_info
            )

        return serialized_component
