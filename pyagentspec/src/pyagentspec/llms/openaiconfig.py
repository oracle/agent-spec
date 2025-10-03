# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""Defines the class for configuring how to connect to a LLM hosted by a vLLM instance."""

from pyagentspec.llms.llmconfig import LlmConfig


class OpenAiConfig(LlmConfig):
    """
    Class to configure a connection to a OpenAI LLM.

    Requires to specify the identity of the model to use.
    """

    model_id: str
    """ID of the model to use"""
