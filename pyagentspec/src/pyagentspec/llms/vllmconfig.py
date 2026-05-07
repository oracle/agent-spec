# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to a LLM hosted by a vLLM instance."""

from typing import Literal

from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig
from pyagentspec.versioning import AgentSpecVersionEnum


class VllmConfig(OpenAiCompatibleConfig):
    """
    Class to configure a connection to a vLLM-hosted LLM.

    Requires to specify the url at which the instance is running.
    """

    api_provider: Literal["vllm"] = "vllm"
    """The API provider used to serve the model."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = super()._versioned_model_fields_to_exclude(agentspec_version)
        # api_provider is frozen/implied by component_type
        fields_to_exclude.add("api_provider")
        return fields_to_exclude
