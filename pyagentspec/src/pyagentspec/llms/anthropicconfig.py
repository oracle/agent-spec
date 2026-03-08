# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to Anthropic Claude models."""


from pydantic import SecretStr

from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.sensitive_field import SensitiveField



class AnthropicLlmConfig(LlmConfig):
    """
    Class to configure a connection to an Anthropic Claude model.

    Requires to specify the model identity. The API key and endpoint are provided by the runtime environment.
    """

    model_id: str
    """ID of the Anthropic model to use, e.g., claude-haiku-4-5-20251001."""

    url: str | None = None
    """URL of the Anthropic API.
    If not provided, the Anthropic API URL from the runtime environment will be used."""

    api_key: SensitiveField[SecretStr | None] = None
    """An optional API KEY for the remote LLM model. If specified, the value of the api_key will be
       excluded and replaced by a reference when exporting the configuration."""
