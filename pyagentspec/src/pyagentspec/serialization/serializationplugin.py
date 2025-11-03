# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
This module defines the interfaces to implement serialization plugins.

Serialization plugins can be invoked during the serialization
process of Agent Spec configurations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pyagentspec.component import Component
from pyagentspec.serialization.serializationcontext import SerializationContext


class ComponentSerializationPlugin(ABC):
    """Base class for Component serialization plugins."""

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
    def serialize(
        self, component: Component, serialization_context: SerializationContext
    ) -> Dict[str, Any]:
        """Serialize a component that the plugin should support."""
        pass

    def __str__(self) -> str:
        """Return the serialization plugin name and version."""
        return f"{self.plugin_name} (version: {self.plugin_version})"
