# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""Defines the class for configuring how to connect to an OpenAI compatible LLM."""

from pyagentspec.llms.llmconfig import LlmConfig


class OpenAiCompatibleConfig(LlmConfig):
    """
    Class to configure a connection to an LLM that is compatible with OpenAI completions APIs.

    Requires to specify the url of the APIs to contact.
    """

    url: str
    """Url of the OpenAI compatible model deployment"""
    model_id: str
    """ID of the model to use"""
