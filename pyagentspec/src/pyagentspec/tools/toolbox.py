# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the base class for toolboxes."""

from typing import Optional

from pyagentspec.component import Component
from pyagentspec.tools.toolpolicy import ToolPolicy
from pyagentspec.versioning import AgentSpecVersionEnum


class ToolBox(Component, abstract=True):
    """A ToolBox is a component that exposes one or more tools to agentic components."""

    requires_confirmation: bool = False
    """Flag to make tool require user confirmation before execution. If set to True, should ask for confirmation for all tools in the ToolBox."""

    tool_policy: Optional[ToolPolicy] = None
    """Governance policy applying to all tools in this ToolBox.

    Individual tools may override or extend this policy. Composition rules:
    stricter data_classification wins, guards are unioned, allowed_callers
    are intersected, requires_justification is ORed.
    """

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v26_2_0:
            fields_to_exclude.add("requires_confirmation")
            fields_to_exclude.add("tool_policy")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        parent_min_version = super()._infer_min_agentspec_version_from_configuration()
        current_object_min_version = self.min_agentspec_version
        if self.requires_confirmation:
            current_object_min_version = AgentSpecVersionEnum.v26_2_0
        if self.tool_policy is not None:
            current_object_min_version = max(
                current_object_min_version, AgentSpecVersionEnum.v26_2_0
            )
        return max(current_object_min_version, parent_min_version)
