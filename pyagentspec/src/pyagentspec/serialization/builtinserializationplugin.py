# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the serialization plugin for builtin Components."""

from pyagentspec._component_registry import BUILTIN_CLASS_MAP
from pyagentspec.serialization.pydanticserializationplugin import (
    PydanticComponentSerializationPlugin,
)


class BuiltinsComponentSerializationPlugin(PydanticComponentSerializationPlugin):
    """Serialization plugin for builtin Components."""

    def __init__(self, _allow_partial_model_serialization: bool = False) -> None:
        """Initialize serialization plugin for builtin components."""
        super().__init__(
            component_types_and_models={
                component_name: component_class
                for component_name, component_class in BUILTIN_CLASS_MAP.items()
                if not component_class._is_abstract
            },
            _allow_partial_model_serialization=_allow_partial_model_serialization,
        )
