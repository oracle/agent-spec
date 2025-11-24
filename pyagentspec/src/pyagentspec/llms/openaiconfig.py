# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to a LLM hosted by a vLLM instance."""

from pyagentspec.component import SerializeAsEnum
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.llms.openaicompatibleconfig import OpenAIAPIType
from pyagentspec.versioning import AgentSpecVersionEnum


class OpenAiConfig(LlmConfig):
    """
    Class to configure a connection to a OpenAI LLM.

    Requires to specify the identity of the model to use.
    """

    model_id: str
    """ID of the model to use"""

    api_type: SerializeAsEnum[OpenAIAPIType] = OpenAIAPIType.CHAT_COMPLETIONS
    """OpenAI API protocol to use"""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("api_type")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        if self.api_type != OpenAIAPIType.CHAT_COMPLETIONS:
            # If the api type is not chat completions, then we need to use the new AgentSpec version
            # If not, the old version will work as it was the de-facto
            return AgentSpecVersionEnum.v25_4_2

        return super()._infer_min_agentspec_version_from_configuration()
