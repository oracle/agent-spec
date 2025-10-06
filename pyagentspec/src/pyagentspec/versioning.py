# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""This module defines the base class for versioning in Agent Spec."""

from enum import Enum

AGENTSPEC_VERSION_FIELD_NAME = "agentspec_version"
"""Name for the field storing the version information"""
_LEGACY_AGENTSPEC_VERSIONS = {"25.3.0", "25.3.1"}
_LEGACY_VERSION_FIELD_NAME = "air_version"


def _version_lt(version1: str, version2: str):
    v1_parts = list(map(int, version1.split(".")))
    v2_parts = list(map(int, version2.split(".")))
    if len(v1_parts) != len(v2_parts):
        raise ValueError(f"Versions should be of same lengths, got {version1} and {version2}")
    return v1_parts < v2_parts


class AgentSpecVersionEnum(Enum):
    v25_3_0 = "25.3.0"
    v25_3_1 = "25.3.1"
    v25_4_1 = "25.4.1"
    current_version = "25.4.1"

    def __lt__(self, other: "AgentSpecVersionEnum"):
        return _version_lt(self.value, other.value)
