# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the base class for versioning in Agent Spec."""

from enum import Enum
from functools import total_ordering

AGENTSPEC_VERSION_FIELD_NAME = "agentspec_version"
"""Name for the field storing the version information"""
_PRERELEASE_AGENTSPEC_VERSIONS = {"25.4.0"}
_LEGACY_AGENTSPEC_VERSIONS = {"25.3.0", "25.3.1", "25.4.0"}
_LEGACY_VERSION_FIELD_NAME = "air_version"


def _version_lt(version1: str, version2: str) -> bool:
    v1_parts = list(map(int, version1.split(".")))
    v2_parts = list(map(int, version2.split(".")))
    if len(v1_parts) != len(v2_parts):
        raise ValueError(f"Versions should be of same lengths, got {version1} and {version2}")
    return v1_parts < v2_parts


@total_ordering
class AgentSpecVersionEnum(Enum):
    """
    An Enumeration for different versions of Agent Spec.
    """

    v25_3_0 = "25.3.0"
    v25_3_1 = "25.3.1"
    v25_4_0 = "25.4.0"
    v25_4_1 = "25.4.1"
    v25_4_2 = "25.4.2"
    v26_1_0 = "26.1.0"
    v26_2_0 = "26.2.0"
    current_version = "26.2.0"

    def __lt__(self, other: "AgentSpecVersionEnum") -> bool:
        return _version_lt(self.value, other.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentSpecVersionEnum):
            raise TypeError(
                f"Equality between AgentSpecVersionEnum and {type(other).__name__} is not supported"
            )
        return self.value == other.value
