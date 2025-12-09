# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines typing aliases for the Agent Spec serialization."""

from collections import UserDict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

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
FieldValue: TypeAlias = Any
"""Alias for the value of a field of a component."""


ComponentsRegistryT: TypeAlias = Mapping[FieldID, Union[Component, FieldValue]]
"""Component registry provided by the user when deserializing a component."""

DisaggregatedComponentsConfigT: TypeAlias = Sequence[
    Union[Component, Tuple[Component, FieldID], Tuple[Component, FieldName, FieldID]]
]
"""Configuration list of components and fields to disaggregated upon serialization."""


class WatchingDict(UserDict[str, str]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.visited: Set[str] = set()

    def get(self, key: str, default: Optional[str] = None) -> str:  # type: ignore
        if key in self.data:
            self.visited.add(key)
            return self.data[key]
        if not default:
            raise ValueError("Should specify default if key is not in dict")
        return default

    def __getitem__(self, key: str) -> str:
        value = super().__getitem__(key)
        self.visited.add(key)
        return value

    def clear_visited(self) -> None:
        self.visited.clear()

    def get_unvisited_keys(self) -> List[str]:
        return [k for k in self.keys() if k not in self.visited]
