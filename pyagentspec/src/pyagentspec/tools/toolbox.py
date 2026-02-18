# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the base class for toolboxes."""


from pyagentspec.component import Component
from pyagentspec.versioning import AgentSpecVersionEnum


class ToolBox(Component, abstract=True):
    """A ToolBox is a component that exposes one or more tools to agentic components."""

    requires_confirmation: bool = False
    """Flag to make tool require user confirmation before execution. If set to True, should ask for confirmation for all tools in the ToolBox."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v26_2_0:
            fields_to_exclude.add("requires_confirmation")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        parent_min_version = super()._infer_min_agentspec_version_from_configuration()
        current_object_min_version = self.min_agentspec_version
        if self.requires_confirmation:
            # If the toolbox has requires confirmation flag set, then we need to use the new AgentSpec version
            # If not, the old version will work as it was the de-facto
            current_object_min_version = AgentSpecVersionEnum.v26_2_0
        return max(current_object_min_version, parent_min_version)
