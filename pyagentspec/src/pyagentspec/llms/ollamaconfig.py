# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Defines the class for configuring how to connect to a LLM hosted by a vLLM instance."""

from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig


class OllamaConfig(OpenAiCompatibleConfig):
    """
    Class to configure a connection to a local model ran with Ollama.

    Requires to specify the url and port at which the model is running.
    """

    pass
