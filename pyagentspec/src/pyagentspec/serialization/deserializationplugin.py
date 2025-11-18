# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
This module defines the interfaces to implement deserialization plugins.

Deserialization plugins can be invoked during the deserialization
process of Agent Spec configurations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from pyagentspec.component import Component
from pyagentspec.serialization.deserializationcontext import DeserializationContext
from pyagentspec.validation_helpers import PyAgentSpecErrorDetails


class ComponentDeserializationPlugin(ABC):
    """Base class for Component deserialization plugins."""

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Return the plugin name."""
        pass

    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """Return the plugin version."""
        pass

    @abstractmethod
    def supported_component_types(self) -> List[str]:
        """Indicate what component types the plugin supports."""
        pass

    @abstractmethod
    def deserialize(
        self, serialized_component: Dict[str, Any], deserialization_context: DeserializationContext
    ) -> Component:
        """Deserialize a serialized component that the plugin should support."""
        pass

    def __str__(self) -> str:
        """Return the deserialization plugin name and version."""
        return f"{self.plugin_name} (version: {self.plugin_version})"

    def _partial_deserialize(
        self, serialized_component: Dict[str, Any], deserialization_context: DeserializationContext
    ) -> Tuple[Component, List[PyAgentSpecErrorDetails]]:
        # By default, the partial deserialization coincides with the full one
        return self.deserialize(serialized_component, deserialization_context), []
