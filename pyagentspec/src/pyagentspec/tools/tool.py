# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the base class for tools."""


from pyagentspec.component import ComponentWithIO
from pyagentspec.versioning import AgentSpecVersionEnum


class Tool(ComponentWithIO, abstract=True):
    """
    A tool specifies a function made available to an agent or a flow.

    It can be bound to one or more agents, which will use it when desired.
    It can be used in a flow by a dedicated tool execution step
    """

    requires_confirmation: bool = False
    """Flag to make tool require user confirmation before execution."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("requires_confirmation")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        parent_min_version = super()._infer_min_agentspec_version_from_configuration()
        current_object_min_version = self.min_agentspec_version
        if self.requires_confirmation:
            # If the tool requires confirmation, then we need to use the new AgentSpec version
            # If not, the old version will work as it was the de-facto
            current_object_min_version = AgentSpecVersionEnum.v25_4_2
        return max(current_object_min_version, parent_min_version)
