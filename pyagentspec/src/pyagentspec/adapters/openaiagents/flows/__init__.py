# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Flows subpackage for OpenAI Agents ↔ PyAgentSpec conversion.

This package provides RulePack-based conversion infrastructure used by the
top-level adapter interfaces. The public flow entrypoints live on
AgentSpecExporter and AgentSpecLoader.
"""

# Ensure rulepacks are registered on import (side-effect import)
from . import rulepacks as _rulepacks  # noqa: F401
from .errors import (
    FlowConversionError,
    LossyMappingError,
    RulePackNotFoundError,
    UnsupportedPatternError,
)

__all__ = [
    "FlowConversionError",
    "UnsupportedPatternError",
    "LossyMappingError",
    "RulePackNotFoundError",
]
