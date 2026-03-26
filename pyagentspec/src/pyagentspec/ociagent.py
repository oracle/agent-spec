# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the OCI Agent component."""

from typing import Optional

from pydantic import SerializeAsAny

from pyagentspec.llms.ociclientconfig import OciClientConfig
from pyagentspec.remoteagent import RemoteAgent
from pyagentspec.retrypolicy import RetryPolicy
from pyagentspec.versioning import AgentSpecVersionEnum


class OciAgent(RemoteAgent):
    """
    An agent is a component that can do several rounds of conversation to solve a task.

    The agent is defined on the OCI console and this is only a wrapper to connect to it.
    It can be executed by itself, or be executed in a flow using an AgentNode.
    """

    agent_endpoint_id: str
    """The OCI AI Agent endpoint identifier for the remote agent."""

    client_config: SerializeAsAny[OciClientConfig]
    """The OCI client configuration used to reach the remote agent service."""

    retry_policy: Optional[RetryPolicy] = None
    """Optional retry configuration for calls sent to the remote OCI agent."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        """Return fields that are not available for the requested Agent Spec version."""

        fields_to_exclude = super()._versioned_model_fields_to_exclude(agentspec_version)
        if agentspec_version < AgentSpecVersionEnum.v26_2_0:
            fields_to_exclude.add("retry_policy")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        """Infer the minimum Agent Spec version required by this OCI agent."""

        min_version = super()._infer_min_agentspec_version_from_configuration()
        if self.retry_policy is not None:
            min_version = max(min_version, AgentSpecVersionEnum.v26_2_0)
        return min_version
