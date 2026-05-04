# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to Gemini LLMs."""

from typing import Literal

from pydantic import Field, SerializeAsAny
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.llms.geminiauthconfig import GeminiAuthConfig
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.versioning import AgentSpecVersionEnum


class GeminiConfig(LlmConfig):
    """Configure a connection to a Gemini LLM (AI Studio or Vertex AI)."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v26_2_0,
        init=False,
        exclude=True,
    )

    auth: SerializeAsAny[GeminiAuthConfig]
    """Authentication configuration used to connect to the Gemini service."""
    provider: Literal["google"] = "google"
    """The provider of the model."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = super()._versioned_model_fields_to_exclude(agentspec_version)
        # provider is frozen/implied by component_type
        fields_to_exclude.add("provider")
        fields_to_exclude.add("url")
        return fields_to_exclude
