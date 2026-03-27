# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to Gemini LLMs."""

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

    model_id: str
    """Identifier of the Gemini model to use."""
    auth: SerializeAsAny[GeminiAuthConfig]
    """Authentication configuration used to connect to the Gemini service."""
