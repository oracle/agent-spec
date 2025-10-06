# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines the deserialization plugin for Pydantic Components."""

from typing import Any, Dict, List, Mapping, Type, cast

from pydantic import BaseModel

from pyagentspec.component import Component
from pyagentspec.serialization.deserializationcontext import DeserializationContext
from pyagentspec.serialization.deserializationplugin import ComponentDeserializationPlugin


class PydanticComponentDeserializationPlugin(ComponentDeserializationPlugin):
    """Deserialization plugin for Pydantic Components."""

    def __init__(self, component_types_and_models: Mapping[str, Type[BaseModel]]) -> None:
        """
        Instantiate a Pydantic deserialization plugin.

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

    def deserialize(
        self, serialized_component: Dict[str, Any], deserialization_context: DeserializationContext
    ) -> Component:
        """Deserialize a serialized Pydantic model."""
        component_type = deserialization_context.get_component_type(serialized_component)
        model_class = self.component_types_and_models[component_type]

        # resolve the content leveraging the pydantic annotations
        resolved_content: Dict[str, Any] = {}
        for field_name, field_info in model_class.model_fields.items():
            annotation = field_info.annotation
            if field_name in serialized_component:
                resolved_content[field_name] = deserialization_context.load_field(
                    serialized_component[field_name], annotation
                )

        # create the component
        component = model_class(**resolved_content)
        return cast(Component, component)
