# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Class to configure a connection to an OCI GenAI hosted model."""
from enum import Enum
from typing import Optional

from pydantic import SerializeAsAny

from pyagentspec.component import SerializeAsEnum
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.llms.ociclientconfig import OciClientConfig
from pyagentspec.versioning import AgentSpecVersionEnum


class OciAPIType(str, Enum):
    """Enumeration of API Types."""

    OPENAI_CHAT_COMPLETIONS = "openai_chat_completions"
    OPENAI_RESPONSES = "openai_responses"
    OCI = "oci"


class ServingMode(str, Enum):
    """Serving mode to use for the GenAI service"""

    ON_DEMAND = "ON_DEMAND"
    DEDICATED = "DEDICATED"


class ModelProvider(str, Enum):
    """Provider of the model. It is used to ensure the requests to this model respect
    the format expected by the provider."""

    META = "META"
    GROK = "GROK"
    COHERE = "COHERE"
    OTHER = "OTHER"


class OciGenAiConfig(LlmConfig):
    """
    Class to configure a connection to a OCI GenAI hosted model.

    Requires to specify the model id and the client configuration to the OCI GenAI service.
    """

    model_id: str
    """The identifier of the model to use."""
    compartment_id: str
    """The OCI compartment ID where the model is hosted."""
    serving_mode: SerializeAsEnum[ServingMode] = ServingMode.ON_DEMAND
    """The serving mode for the model."""
    provider: Optional[SerializeAsEnum[ModelProvider]] = None
    """The provider of the model. If None, it will be automatically detected by the runtime using the model ID."""
    client_config: SerializeAsAny[OciClientConfig]
    """The client configuration for connecting to OCI GenAI service."""
    api_type: SerializeAsEnum[OciAPIType] = OciAPIType.OCI
    """API protocol to use."""
    conversation_store_id: Optional[str] = None
    """ID of the conversation store to persist conversations when using the openai responses API."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("api_type")
            fields_to_exclude.add("conversation_store_id")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        parent_min_version = super()._infer_min_agentspec_version_from_configuration()
        current_object_min_version = self.min_agentspec_version
        if self.conversation_store_id is not None:
            # `conversation_store_id` is only introduced starting from 25.4.2
            current_object_min_version = AgentSpecVersionEnum.v25_4_2
        if self.api_type != OciAPIType.OCI:
            # If the api type is not the original oci APIs, then we need to use the new AgentSpec version
            # If not, the old version will work as it was the de-facto
            current_object_min_version = AgentSpecVersionEnum.v25_4_2
        return max(current_object_min_version, parent_min_version)
