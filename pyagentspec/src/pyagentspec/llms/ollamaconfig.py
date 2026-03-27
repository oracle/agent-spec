# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to a LLM hosted by Ollama."""

from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig
from pyagentspec.versioning import AgentSpecVersionEnum


class OllamaConfig(OpenAiCompatibleConfig):
    """
    Class to configure a connection to a local model ran with Ollama.

    Requires to specify the url and port at which the model is running.
    """

    api_provider: str = "ollama"
    """The API provider used to serve the model."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = super()._versioned_model_fields_to_exclude(agentspec_version)
        # api_provider is frozen/implied by component_type
        fields_to_exclude.add("api_provider")
        return fields_to_exclude
