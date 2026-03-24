# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the classes for configuring Gemini authentication."""

from typing import Any, Dict, Optional

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.component import Component
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.versioning import AgentSpecVersionEnum


class GeminiAuthConfig(Component, abstract=True):
    """Base class for Gemini authentication configuration."""

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v26_2_0,
        init=False,
        exclude=True,
    )


class GeminiAIStudioAuthConfig(GeminiAuthConfig):
    """Authentication settings for Gemini via Google AI Studio."""

    api_key: SensitiveField[Optional[str]] = None
    """API key to use. If unset, runtimes may load it from ``GEMINI_API_KEY``."""


class GeminiVertexAIAuthConfig(GeminiAuthConfig):
    """Authentication settings for Gemini via Google Vertex AI."""

    project_id: Optional[str] = None
    """Optional Google Cloud project identifier.

    This may still need to be set explicitly when the runtime cannot infer the
    project from Application Default Credentials (ADC) or other local Google
    Cloud configuration.
    """
    location: str = "global"
    """Vertex AI location/region."""
    credentials: SensitiveField[Optional[str | Dict[str, Any]]] = None
    """Optional local file path to a Google Cloud JSON credential file, such as a
    service-account key file, or an inline dictionary containing the parsed JSON
    contents of that file.

    When unset, runtimes may rely on Application Default Credentials (ADC), such as
    ``GOOGLE_APPLICATION_CREDENTIALS``, credentials made available through the local
    Google Cloud environment, or an attached service account.
    Even then, ``project_id`` may still need to be provided separately if it
    cannot be resolved from the environment.
    """
