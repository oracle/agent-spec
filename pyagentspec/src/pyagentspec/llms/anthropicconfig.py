# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to Anthropic Claude models."""

from pyagentspec.llms.llmconfig import LlmConfig


class AnthropicLlmConfig(LlmConfig):
    """
    Class to configure a connection to an Anthropic Claude model.

    Requires to specify the model identity. The API key and endpoint are provided by the runtime environment.
    """

    model_id: str
    """ID of the Anthropic model to use, e.g., claude-haiku-4-5-20251001."""

    base_url: str | None = None
    """Base URL of the Anthropic API.
    If not provided, the default Anthropic API base URL will be used."""
