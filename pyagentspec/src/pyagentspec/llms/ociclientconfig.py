# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to a OCI GenAI client."""

from typing import Literal, Optional

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from pyagentspec.component import Component
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.versioning import AgentSpecVersionEnum


class OciClientConfig(Component, abstract=True):
    """Base abstract class for OCI client config."""

    service_endpoint: str
    auth_type: Literal[
        "SECURITY_TOKEN", "INSTANCE_PRINCIPAL", "RESOURCE_PRINCIPAL", "API_KEY", "GENAI_API_KEY"
    ]


class OciClientConfigWithSecurityToken(OciClientConfig):
    """OCI client config class for authentication using SECURITY_TOKEN."""

    auth_profile: str
    auth_file_location: SensitiveField[str]
    auth_type: Literal["SECURITY_TOKEN"] = "SECURITY_TOKEN"


class OciClientConfigWithInstancePrincipal(OciClientConfig):
    """OCI client config class for authentication using INSTANCE_PRINCIPAL."""

    auth_type: Literal["INSTANCE_PRINCIPAL"] = "INSTANCE_PRINCIPAL"


class OciClientConfigWithResourcePrincipal(OciClientConfig):
    """OCI client config class for authentication using RESOURCE_PRINCIPAL."""

    auth_type: Literal["RESOURCE_PRINCIPAL"] = "RESOURCE_PRINCIPAL"


class OciClientConfigWithApiKey(OciClientConfig):
    """OCI client config class for authentication using API_KEY and a config file."""

    auth_profile: str
    auth_file_location: SensitiveField[str]
    auth_type: Literal["API_KEY"] = "API_KEY"


class OciClientConfigWithGenAiApiKey(OciClientConfig):
    """OCI client config class for authentication using an OCI Generative AI API key.

    Generative AI API keys are created in the OCI Generative AI service, are scoped to a
    compartment and a region, and are sent as a bearer token to the OpenAI-compatible API of the
    service (``<service_endpoint>/openai/v1``). They require neither an OCI configuration file nor
    request signing. They only authorize model inference, so this client configuration cannot be
    used to reach other OCI services such as the Agents service.
    """

    api_key: SensitiveField[Optional[str]] = None
    """The Generative AI API key. If unset, runtimes may load it from ``OCI_GENAI_API_KEY``."""
    auth_type: Literal["GENAI_API_KEY"] = "GENAI_API_KEY"

    min_agentspec_version: SkipJsonSchema[AgentSpecVersionEnum] = Field(
        default=AgentSpecVersionEnum.v26_4_0, init=False, exclude=True
    )
