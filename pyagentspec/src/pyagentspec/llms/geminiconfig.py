# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the classes for configuring how to connect to Gemini LLMs."""

from typing import Annotated, Any, Dict, Literal, Optional, TypeAlias

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.versioning import AgentSpecVersionEnum


class GeminiAiStudioAuthConfig(BaseModel):
    """Authentication settings for Gemini via Google AI Studio."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["aistudio"] = "aistudio"
    """Discriminator for the Gemini AI Studio authentication mode."""
    api_key: Optional[str] = None
    """API key to use. If unset, runtimes may load it from ``GEMINI_API_KEY``."""


class GeminiVertexAiAuthConfig(BaseModel):
    """Authentication settings for Gemini via Google Vertex AI."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["vertex_ai"] = "vertex_ai"
    """Discriminator for the Gemini Vertex AI authentication mode."""
    project_id: Optional[str] = None
    """Optional Google Cloud project identifier.

    This may still need to be set explicitly when the runtime cannot infer the
    project from Application Default Credentials (ADC) or other local Google
    Cloud configuration.
    """
    location: str = "global"
    """Vertex AI location/region."""
    credentials: Optional[str | Dict[str, Any]] = None
    """Optional service-account JSON file path or inline service-account JSON object.

    When unset, runtimes may rely on Application Default Credentials (ADC), such as
    ``GOOGLE_APPLICATION_CREDENTIALS``, credentials configured via
    ``gcloud auth application-default login``, or an attached service account.
    Even then, ``project_id`` may still need to be provided separately if it
    cannot be resolved from the environment.
    """


GeminiAuthConfig: TypeAlias = Annotated[
    GeminiAiStudioAuthConfig | GeminiVertexAiAuthConfig,
    Field(discriminator="type"),
]


class GeminiConfig(LlmConfig):
    """Configure a connection to a Gemini LLM (AI Studio or Vertex AI)."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v26_2_0,
        init=False,
        exclude=True,
    )

    model_id: str
    """Identifier of the Gemini model to use."""
    auth: SensitiveField[GeminiAuthConfig]
    """Authentication configuration used to connect to the Gemini service."""
