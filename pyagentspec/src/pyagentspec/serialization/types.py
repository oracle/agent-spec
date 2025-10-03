# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines typing aliases for the Agent Spec serialization."""

from collections import UserDict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from typing_extensions import TypeAlias

from pyagentspec.component import Component

ComponentAsDictT = Dict[str, Any]
"""Serialized dictionary of a Component"""

DisaggregatedComponentsAsDictT = Dict[str, Any]
"""Serialized dictionary of disaggregated Components"""

BaseModelAsDictT = Dict[str, Any]
"""Serialized dictionary of Pydantic models."""


class _DeserializationInProgressMarker:
    pass


LoadedReferencesT = Dict[str, Union[_DeserializationInProgressMarker, Component]]

FieldName: TypeAlias = str
"""Alias for a component field name."""
FieldID: TypeAlias = str
"""Alias for a component field ID."""


ComponentsRegistryT: TypeAlias = Mapping[FieldID, Union[Component, Tuple[Component, FieldName]]]
"""Component registry provided by the user when deserializing a component."""

DisaggregatedComponentsConfigT: TypeAlias = Sequence[
    Union[Component, Tuple[Component, FieldID], Tuple[Component, FieldName, FieldID]]
]
"""Configuration list of components and fields to disaggregated upon serialization."""


class WatchingDict(UserDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited = set()

    def get(self, key, default=None):
        if key in self.data:
            self.visited.add(key)
            return self.data[key]
        return default

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.visited.add(key)
        return value

    def clear_visited(self):
        self.visited.clear()

    def get_unvisited_keys(self) -> Optional[List[str]]:
        return [k for k in self.keys() if k not in self.visited]
