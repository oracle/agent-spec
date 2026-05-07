# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines the base class for all LLM configuration component."""

from typing import Optional

from pyagentspec.component import Component
from pyagentspec.llms.llmgenerationconfig import LlmGenerationConfig
from pyagentspec.retrypolicy import RetryPolicy
from pyagentspec.sensitive_field import SensitiveField
from pyagentspec.versioning import AgentSpecVersionEnum


class LlmConfig(Component):
    """
    A LLM configuration defines how to connect to a LLM to do generation requests.

    This class can be used directly with the ``provider``, ``api_provider``, and ``api_type``
    fields to describe any LLM without a dedicated subclass. Concrete subclasses provide
    additional configuration for specific LLM providers.
    """

    model_id: str
    """Identifier of the model to use, as expected by the selected API provider."""

    provider: Optional[str] = None
    """The provider of the model (e.g. 'meta', 'openai', 'cohere')."""

    api_provider: Optional[str] = None
    """The API provider used to serve the model (e.g. 'openai', 'oci', 'vllm')."""

    api_type: Optional[str] = None
    """The API format to use (e.g. 'chat_completions', 'responses')."""

    url: Optional[str] = None
    """URL of the API endpoint (e.g. 'https://api.openai.com/v1')."""

    api_key: SensitiveField[Optional[str]] = None
    """An optional API key for the remote LLM model. If specified, the value of the api_key will be
       excluded and replaced by a reference when exporting the configuration."""

    default_generation_parameters: Optional[LlmGenerationConfig] = None
    """Parameters used for the generation call of this LLM"""

    retry_policy: Optional[RetryPolicy] = None
    """Optional retry configuration for remote LLM calls."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = super()._versioned_model_fields_to_exclude(agentspec_version)
        # All these attributes were introduced in Agent Spec 26.2.0.
        if agentspec_version < AgentSpecVersionEnum.v26_2_0:
            fields_to_exclude.add("retry_policy")
            fields_to_exclude.add("provider")
            fields_to_exclude.add("api_key")
            fields_to_exclude.add("api_type")
            fields_to_exclude.add("api_provider")
            fields_to_exclude.add("url")
            fields_to_exclude.add("model_id")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        min_version = super()._infer_min_agentspec_version_from_configuration()
        if self.retry_policy is not None:
            min_version = max(min_version, AgentSpecVersionEnum.v26_2_0)
        # Bare LlmConfig is a v26_2_0 feature — it was abstract before.
        # Subclasses handle their own versioning independently.
        if type(self) is LlmConfig:
            min_version = max(AgentSpecVersionEnum.v26_2_0, min_version)
        return min_version
