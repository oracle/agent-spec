# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to an OpenAI LLM."""

from typing import Literal, Optional

from pyagentspec.component import SerializeAsEnum
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.llms.openaicompatibleconfig import OpenAIAPIType
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.versioning import AgentSpecVersionEnum


class OpenAiConfig(LlmConfig):
    """
    Class to configure a connection to a OpenAI LLM.

    Requires to specify the identity of the model to use.
    """

    provider: Literal["openai"] = "openai"
    """The provider of the model."""

    api_provider: Literal["openai"] = "openai"
    """The API provider used to serve the model."""

    api_type: SerializeAsEnum[OpenAIAPIType] = OpenAIAPIType.CHAT_COMPLETIONS
    """OpenAI API protocol to use"""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = super()._versioned_model_fields_to_exclude(agentspec_version)
        # First, we reintroduce the attributes that were introduced in 26.2.0 LlmConfig, but were
        # already here before that version. Then the rest of the logic will handle older versions.
        if agentspec_version < AgentSpecVersionEnum.v26_2_0:
            fields_to_exclude.remove("api_type")
            fields_to_exclude.remove("api_key")
            fields_to_exclude.remove("model_id")
        # provider and api_provider are frozen/implied by component_type
        fields_to_exclude.add("provider")
        fields_to_exclude.add("api_provider")
        fields_to_exclude.add("url")
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("api_type")
            fields_to_exclude.add("api_key")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        parent_min_version = super()._infer_min_agentspec_version_from_configuration()
        current_object_min_version = self.min_agentspec_version
        if self.api_key is not None:
            # `api_key` is only introduced starting from 25.4.2
            current_object_min_version = AgentSpecVersionEnum.v25_4_2
        if self.api_type != OpenAIAPIType.CHAT_COMPLETIONS:
            # If the api type is not chat completions, then we need to use the new AgentSpec version
            # If not, the old version will work as it was the de-facto
            current_object_min_version = AgentSpecVersionEnum.v25_4_2
        return max(current_object_min_version, parent_min_version)
