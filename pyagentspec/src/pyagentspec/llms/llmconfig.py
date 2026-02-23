# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the base class for all LLM configuration component."""

from typing import Optional

from pyagentspec.component import Component
from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig
from pyagentspec.retrypolicy import RetryPolicy
from pyagentspec.versioning import AgentSpecVersionEnum


class LlmConfig(Component, abstract=True):
    """
    A LLM configuration defines how to connect to a LLM to do generation requests.

    This class provides the base class, while concrete classes provide the required
    configuration to connect to specific LLM providers.
    """

    default_generation_parameters: Optional[LlmGenerationConfig] = None
    """Parameters used for the generation call of this LLM"""

    retry_policy: Optional[RetryPolicy] = None
    """Optional retry configuration for remote LLM calls."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = super()._versioned_model_fields_to_exclude(agentspec_version)
        # `retry_policy` was introduced in Agent Spec 26.2.0.
        if agentspec_version < AgentSpecVersionEnum.v26_2_0:
            fields_to_exclude.add("retry_policy")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        min_version = super()._infer_min_agentspec_version_from_configuration()
        if self.retry_policy is not None:
            min_version = max(min_version, AgentSpecVersionEnum.v26_2_0)
        return min_version
